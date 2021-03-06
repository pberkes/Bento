import os
import sys
import re

from bento._config \
    import \
        _CLI

from bento.installed_package_description \
    import \
        InstalledSection

SYS_EXECUTABLE = os.path.normpath(sys.executable)

SCRIPT_TEXT = """\
# BENTO AUTOGENERATED-CONSOLE SCRIPT
if __name__ == '__main__':
    import sys
    from %(module)s import %(function)s
    sys.exit(%(function)s())
"""

_LAUNCHER_MANIFEST = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
 <assemblyIdentity version="1.0.0.0"
 processorArchitecture="X86"
 name="%s.exe"
 type="win32"/>

 <!-- Identify the application security requirements. -->
 <trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
 <security>
 <requestedPrivileges>
 <requestedExecutionLevel level="asInvoker" uiAccess="false"/>
 </requestedPrivileges>
 </security>
 </trustInfo>
</assembly>"""

# XXX: taken from setuptools, audit this
def nt_quote_arg(arg):
    """Quote a command line argument according to Windows parsing
    rules"""

    result = []
    needquote = False
    nb = 0

    needquote = (" " in arg) or ("\t" in arg)
    if needquote:
        result.append('"')

    for c in arg:
        if c == '\\':
            nb += 1
        elif c == '"':
            # double preceding backslashes, then add a \"
            result.append('\\' * (nb*2) + '\\"')
            nb = 0
        else:
            if nb:
                result.append('\\' * nb)
                nb = 0
            result.append(c)

    if nb:
        result.append('\\' * nb)

    if needquote:
        result.append('\\' * nb)    # double the trailing backslashes
        result.append('"')

    return ''.join(result)

# XXX: taken verbatim from setuptools, rewrite this crap
def get_script_header(executable=SYS_EXECUTABLE, wininst=False):
    from distutils.command.build_scripts import first_line_re

    match = first_line_re.match("")

    options = ''
    if match:
        options = match.group(1) or ''
        if options:
            options = ' ' + options
    if wininst:
        executable = "python.exe"
    else:
        executable = nt_quote_arg(executable)

    hdr = "#!%(executable)s%(options)s\n" % locals()
    if unicode(hdr,'ascii','ignore').encode('ascii') != hdr:
        # Non-ascii path to sys.executable, use -x to prevent warnings
        if options:
            if options.strip().startswith('-'):
                options = ' -x' + options.strip()[1:]
            # else: punt, we can't do it, let the warning happen anyway
        else:
            options = ' -x'
    #executable = fix_jython_executable(executable, options)
    hdr = "#!%(executable)s%(options)s\n" % locals()
    return hdr

def create_scripts(executables, bdir):
    ret = {}

    for name, executable in executables.items():
        if sys.platform == "win32":
            ret[name] = create_win32_script(name, executable, bdir)
        else:
            ret[name] = create_posix_script(name, executable, bdir)
    return ret

def create_win32_script(name, executable, scripts_node):
    script_text = SCRIPT_TEXT % {"python_exec": SYS_EXECUTABLE,
            "module": executable.module,
            "function": executable.function}

    wininst = False
    header = get_script_header(SYS_EXECUTABLE, wininst)

    ext = '-script.py'
    launcher = _CLI

    old = ['.py','.pyc','.pyo']
    new_header = re.sub('(?i)pythonw.exe', 'python.exe', header)

    if os.path.exists(new_header[2:-1]) or sys.platform != 'win32':
        hdr = new_header
    else:
        hdr = header

    fid = open(launcher, "rb")
    try:
        cnt = fid.read()
    finally:
        fid.close()

    def _write(name, cnt, mode):
        target = scripts_node.make_node(name)
        target.safe_write(cnt, "w%s" % mode)
        return target

    nodes = []
    nodes.append(_write(name + ext, hdr + script_text, 't'))
    nodes.append(_write(name + ".exe", cnt, 'b'))
    nodes.append(_write(name + ".exe.manifest", _LAUNCHER_MANIFEST % (name,), 't'))

    return nodes

def create_posix_script(name, executable, scripts_node):
    header = "#!%(python_exec)s\n" % {"python_exec": SYS_EXECUTABLE}
    cnt = SCRIPT_TEXT % {"python_exec": SYS_EXECUTABLE,
            "module": executable.module,
            "function": executable.function}

    n = scripts_node.make_node(name)
    n.safe_write(header + cnt)
    return [n]

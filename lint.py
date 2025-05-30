import os
import sys

LINT_DEFAULT_IGNORES = ['C0103', 'C0111',
                        'W0622', 'W0702', 'R0913',
                        'W0401', 'W0703', 'W0603']


def lint(file=None, output_file=None, ignore=[], extras='', default_ignores=True):
    import pylint.lint
    ignore = default_ignores and ignore + LINT_DEFAULT_IGNORES or ignore
    file = file or sys.argv[0]
    if output_file is sys.stdout:
        output_file = ''
    elif output_file is None:
        output_file = os.path.splitext(file)[0] + '.lint.txt'
    # do i really need this to be r'""%s" -m...', with 2 " at the start?
    command = '""%s" -m pylint.lint --include-ids=y%s%s%s%s' \
              % (sys.executable.replace('pythonw.exe', 'python.exe'),
                 ignore and ' --disable=' + ','.join(ignore) or '',
                 extras and ' %s ' % extras or '',
                 ' "%s"' % file,
                 output_file and ' > "%s"' % output_file or '')
    command = ['--extension-pkg-whitelist=pygame']
    if ignore:
        command.append('--disable=' + ','.join(ignore))
    if extras:
        command.append(extras)
    if output_file:
        command.append('--output=%s' % (output_file))
    command.append(file)
    print(command)
    pylint.lint.Run(command, exit=False)


def lint_many(files=[], output_folder=None, ignore=[], extras='', default_ignore=True):
    for i in files:
        f = os.path.join(output_folder, os.path.split(i)[0])
        if not os.path.exists(f):
            os.makedirs(f)
        lint(i, os.path.join(output_folder, i + 'LINT.txt'), ignore, extras, default_ignore)

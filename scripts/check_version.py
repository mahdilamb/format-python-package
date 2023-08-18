import subprocess, re, pkg_resources, sys


path, variable, default_branch = sys.argv[1:4]
print(subprocess.run(f"git show {default_branch}:{path}", capture_output=True))
version_pattern = re.compile(rf"^{variable}.*?=.*?[''\"](.*?)[''\"]", flags=re.M)
to_version = lambda cmd: pkg_resources.parse_version(
    version_pattern.findall(
        subprocess.run(cmd, capture_output=True, shell=True).stdout.decode()
    )[0]
)
main = to_version(f"git show main:{path}")
current = to_version(f"cat {path}")
assert (
    main < current
), f"Version of current commit ({current}) has not been incremented (from {main})."

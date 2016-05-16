from util import github_repo_url, order_repos_index

from buildbot.process.factory import BuildFactory
from buildbot.plugins import steps
from buildbot.config import BuilderConfig


class Builders(object):

    def __init__(self, config, slaves, repos):
        self.config = config
        self.slaves = slaves
        self.repos = repos

    def create_builder(self, repo_name):
        builder_name = 'builder_' + repo_name
        venv_name = "virtualenv_ci_" + builder_name
        venv_path = {'PATH':  "./" + venv_name + '/bin' + ':${PATH}'}
        venv_path_factory = {'PATH':  "../" + venv_name + '/bin' + ':${PATH}'}

        factory = BuildFactory()
        factory.addSteps([
            steps.ShellCommand(command=["rm", "-rf", venv_name], haltOnFailure=True,
                         workdir=".", name="Remove previous virtualenv"),
            steps.ShellCommand(command=["virtualenv", "--python=python2", venv_name],
                         haltOnFailure=True, workdir=".",
                         name="Create new virtualenv"),
            steps.ShellCommand(
                command=['pip', 'install', '-U', 'pip', 'setuptools',
                         'coverage'],
                env=venv_path, workdir=".", name="Update setuptools")
        ])

        repo_index = [repo[order_repos_index] for repo in self.repos if repo[0] is repo_name][0]
        for repo_name, repo_branch, _, namespace, in sorted(self.repos, key = lambda repo: repo[order_repos_index])[0:repo_index]:
            _add_repo_to_factory(factory, repo_name, repo_branch, namespace, venv_name)

        factory.addSteps([
            steps.ShellCommand(command=['pep8', '.'],env=venv_path_factory,haltOnFailure=False, workdir=repo_name, name="pep8 on " + repo_name)])

        if namespace is not '':
            if repo_name is 'bitmask_client':
                factory.addStep(
                    steps.ShellCommand(command=['xvfb-run', 'coverage', 'run', '--omit=*/'+venv_name+'/*', venv_name + '/bin/trial', namespace], env=venv_path, workdir='.', name="trial "+namespace))
            else:
                factory.addStep(
                    steps.ShellCommand(command=['coverage', 'run', '--omit=*/'+venv_name+'/*', venv_name + '/bin/trial', namespace], env=venv_path, workdir='.', name="trial "+namespace))

            factory.addSteps([
                steps.ShellCommand(
			command=['coverage', 'html'], env=venv_path, workdir='.',
			name="generate html coverage report for " +namespace),
                steps.ShellCommand(
			command=self._publish_coverage_reports_command(
				'htmlcov', repo_name), workdir='.',
				doStepIf=(
					lambda step: self.slaves.is_leap(step.getProperty('slavename'))))
            ])

        self._publish_leap_wheels(
	    factory, repo_name, venv_path_factory, doStepIf=(lambda step: self.slaves.is_leap(step.getProperty('slavename'))))

        if repo_name == 'bitmask_client':
            publish_sumo = self._publish_sumo_command('`ls -t *SUMO.tar.gz | head -1`')

            factory.addSteps([
                steps.ShellCommand(command=['make', 'sumo_tarball_latest'],
                              env=venv_path_factory, workdir=repo_name,
                              doStepIf=(lambda step: self.slaves.is_leap(step.getProperty('slavename'))),
                              name="make sumo tarball"),
                steps.ShellCommand(command=publish_sumo,
                              env=venv_path_factory, workdir=repo_name + "/dist",
                              doStepIf=(lambda step: self.slaves.is_leap(step.getProperty('slavename'))),
                              name="publish sumo to ftp")
                ])


        return BuilderConfig(name=builder_name, slavenames=self.slaves.names(), factory=factory)

    def _publish_coverage_reports_command(self, location, repo_name):
        target_directory = self.config.get('ftp', 'coverage_reports_target_directory') + '/' + repo_name + '_' + '`git -C ' + repo_name + ' describe`'
        return self._ftp_publish_dir_command(location, target_directory)

    def _publish_leap_wheels(self, factory, repo_name, env, doStepIf):
        env_soledad = {'PATH':  env['PATH'].replace('../', '../../', 1)}

        if repo_name == 'soledad':
            for subpackage in ["common", "client", "server"]:
                factory.addSteps([
                    steps.ShellCommand(
			command=['python', 'setup.py', 'bdist_wheel'],
			env=env_soledad, doStepIf=doStepIf, haltOnFailure=True, 
			workdir=repo_name+'/'+subpackage,
			name="leap wheels for " + repo_name+"."+subpackage),
                    steps.ShellCommand(
			command=self._publish_leap_wheels_soledad(
			    subpackage, '`ls -t *.whl | head -1`'),
			env=env_soledad, doStepIf=doStepIf, haltOnFailure=True,
			workdir=repo_name+'/'+subpackage+'/dist',
			name="publish leap wheels for " + repo_name+"."+subpackage)])
        else:
            factory.addSteps([
                steps.ShellCommand(
			command=['python', 'setup.py', 'bdist_wheel'],
			env=env, doStepIf=doStepIf,
			#workdir='build/',
			workdir=repo_name,
			name="Generate leap wheels for "+repo_name),
                steps.ShellCommand(
			command=self._publish_leap_wheels_command(
			    repo_name, '`ls -t *.whl | head -1`'),
			env=env, doStepIf=doStepIf,
			workdir=repo_name + '/dist/',
			name="Publish leap wheels for "+repo_name)
            ])

    def _publish_leap_wheels_command(self, repo_name, location):
        directory = self.config.get('ftp', 'leap_wheels_directory')
        command = self._ftp_publish_command(location, directory) + ' && ' + self._ftp_soft_link(location, directory, 'leap.' + repo_name + '-latest.whl')

        return command

    def _publish_leap_wheels_soledad(self, subpackage, location):
        directory = self.config.get('ftp', 'leap_wheels_directory')
        command = self._ftp_publish_command(location, directory) + ' && ' + self._ftp_soft_link(location, directory, 'leap.soledad.' + subpackage + '-latest.whl')

        return command

    def _publish_sumo_command(self, location):
        directory = self.config.get('ftp', 'sumo_target_directory')
        ftp = self._ftp_publish_command(location, directory)
        link = self._ftp_soft_link(
            location, directory, 'leap.bitmask-latest-SUMO.tar.gz')
        command = ftp + ' && ' + link

        return command

    def _ftp_soft_link(self, filename, target_directory, symlink_name):
        return self._ftp_ssh_command('ln -sf ' + target_directory + '/' + filename + ' ' + target_directory + '/' + symlink_name)

    def _ftp_ssh_command(self, command):
        ssh_port = self.config.get('ftp', 'ssh_port')
        ssh_key = self.config.get('ftp', 'ssh_key')
        user = self.config.get('ftp', 'user')
        server = self.config.get('ftp', 'server')

        ssh_command = ['ssh',
                       "-i", ssh_key,
                       '-p', ssh_port,
                       user + '@' + server,
                       '"' + command + '"']

        # Flatten to a string so that a shell executes de command, and
        # expands ~
        return ' '.join(ssh_command)

    def _ftp_publish_dir_command(self, from_dir, to_dir):
        return self._ftp_publish_command(from_dir + "/*", to_dir)

    def _ftp_publish_command(self, from_location, to_location):
        ssh_port = self.config.get('ftp', 'ssh_port')
        ssh_key = self.config.get('ftp', 'ssh_key')
        user = self.config.get('ftp', 'user')
        server = self.config.get('ftp', 'server')

        ssh_mkdir_command = ['ssh',
                             "-i", ssh_key,
                             '-p', ssh_port,
                             user + '@' + server,
                             '"mkdir -p ' + to_location + '"']

        scp_command = ['scp',
                       '-i', ssh_key,
                       '-P', ssh_port,
                       '-r', from_location,
                       '"' + user + '@' + server + ':' + to_location +'"']
        ssh_command = ['ssh',
                       "-i", ssh_key,
                       '-p', ssh_port,
                       user + '@' + server,
                       '"chmod -R g+r ' + to_location + ' && chown -R ' + user + ':www-data ' + to_location + '"']
        # Flatten to a string so that a shell executes de command, and
        # expands ~
        return ' '.join(ssh_mkdir_command) + ' ; ' + ' '.join(scp_command) + ' && ' + ' '.join(ssh_command)

    def make_wheel_builder(self):
        builder_name = "builder_wheels"
        venv_name = "virtualenv_wheels"
        factory = BuildFactory()

        generate_wheels = 'pkg/generate_wheels.sh'
        publish_wheels = self._publish_wheels_command()

        sandbox_path_top = {'PATH':  "./" + venv_name + '/bin' + ':${PATH}'}
        sandbox_path = {'PATH':  "../" + venv_name + '/bin' + ':${PATH}'}
        sandbox_path_soledad = {'PATH':  "../../" + venv_name + '/bin/' + ':${PATH}'}

        factory.addStep(steps.ShellCommand(command=["virtualenv", "--python=python2", venv_name], haltOnFailure=True, workdir=".", name="Create new virtualenv"))
        factory.addStep(steps.ShellCommand(command=['pip', 'install', '-U', 'wheel'], env=sandbox_path_top, haltOnFailure=True, workdir=".", name="Install wheels"))
        for repo_name, git_branch, _, _ in self.repos:
            repo_url = github_repo_url(repo_name)
            workdir = repo_name
            factory.addStep(
                steps.Git(repourl=repo_url, branch=git_branch, workdir=workdir, mode='full', method='clobber', shallow=True, haltOnFailure=True, name="Pull " + repo_url))
            if 'soledad' in repo_name:
                for subpackage in ["common", "client", "server"]:
                    factory.addStep(
                        steps.ShellCommand(command=generate_wheels, env=sandbox_path_soledad, haltOnFailure=True, workdir=workdir+'/'+subpackage, name="wheels for " + repo_name+"."+subpackage))
            else:
                factory.addStep(
                    steps.ShellCommand(command=generate_wheels, env=sandbox_path, haltOnFailure=True, workdir=workdir, name="wheels for " + repo_name))
        factory.addStep(steps.ShellCommand(command=publish_wheels, env=sandbox_path, doStepIf=(lambda step: self.slaves.is_leap(step.getProperty('slavename'))), workdir=".", name="publish wheels"))

        self._add_pyside_setup_repo(factory)

        return BuilderConfig(name=builder_name, slavenames=self.slaves.names(), factory=factory)

    def _publish_wheels_command(self):
        original_wheelhouse = self.config.get('ftp', 'copy_wheels_from')
        directory = self.config.get('ftp', 'directory')

        return self._ftp_publish_dir_command(original_wheelhouse, directory)

    def _add_pyside_setup_repo(self, factory):
        repo_name = "pyside-setup"
        repo_url = "https://github.com/ivanalejandro0/" + repo_name + ".git"
        git_branch = "master"
        
        venv_name = "virtualenv_wheels"
        sandbox_path = {'PATH':  "../" + venv_name + '/bin' + ':${PATH}'}

        publish_pyside_wheel = self._publish_pyside_command('`ls -t *.whl | head -1`')
        factory.addSteps([
            steps.ShellCommand(command=['rm', '-rf', repo_name], workdir='.', env=sandbox_path, name="Remove previous pyside"),
            steps.Git(repourl=repo_url, branch=git_branch, workdir=repo_name, mode='full', method='clobber', shallow=True, haltOnFailure=True, name="Pull " + repo_url),
            steps.ShellCommand(command=['python', 'setup.py', 'bdist_wheel', '--standalone'], workdir=repo_name, env=sandbox_path, name="Wheel for " + repo_name),
            steps.ShellCommand(command=publish_pyside_wheel, workdir=repo_name + '/dist/', name="Publish pyside")
        ])

    def _publish_pyside_command(self, location):
        directory = self.config.get('ftp', 'directory')
        command = self._ftp_publish_command(location, directory)

        return command

    def make_bundler_builder(self):
        builder_name = "builder_bundler"
        factory = BuildFactory()
        repo_name = "bitmask_bundler"
        repo_url = "https://github.com/leapcode/" + repo_name + ".git"
        branch = "develop"

        workdir="build"
        repo_dir = workdir + "/" + repo_name
        bundler_output_dir = "bundler_output"
        sumo_tarball = "leap.bitmask-latest-SUMO.tar.gz"

        publish_bundle = self._publish_bundle_command('`ls -t *.tar.gz | head -1`')

        factory.addSteps([
            steps.Git(repourl=repo_url, branch=branch, workdir=repo_dir, mode='full', method='clobber', shallow=True, haltOnFailure=True, name="Pull " + repo_url),
            steps.ShellCommand(command="rm -rf " + bundler_output_dir, workdir=workdir, name="Remove previous bundler dir"),
            steps.ShellCommand(command="mkdir " + bundler_output_dir, workdir=workdir, name="Create bundler dir"),
            steps.ShellCommand(command="cp bundle_pyinstaller.sh ../" + bundler_output_dir, workdir=repo_dir, haltOnFailure=True, name="Copy bundle_pyinstaller"),
            steps.ShellCommand(command="mkdir files", workdir=workdir + '/' + bundler_output_dir, name="Create auxiliary folder"),
            steps.ShellCommand(command="wget http://lizard.leap.se/sumo-tarball/" + sumo_tarball, workdir=workdir + '/' + bundler_output_dir, haltOnFailure=True, name="Download sumo"),
            steps.ShellCommand(command="./bundle_pyinstaller.sh " + sumo_tarball, workdir=workdir + '/' + bundler_output_dir, name="Create bundle"),
            steps.ShellCommand(command=publish_bundle, workdir=workdir + '/' + bundler_output_dir, name="Publish bundle")
        ])

        return BuilderConfig(name=builder_name, slavenames=self.slaves.leap_names(), factory=factory)

    def _publish_bundle_command(self, location):
        directory = self.config.get('ftp', 'bundle_target_directory')
        command = self._ftp_publish_command(location, directory) + ' && ' + self._ftp_soft_link(location, directory, 'bitmask-latest.tar.gz')

        return command


def _add_repo_to_factory(factory, repo_name, git_branch, namespace, venv_name):
    install_requirements = (
        "pkg/pip_install_requirements.sh --use-leap-wheels")
    install_requirements_tests = """
        if [ -f pkg/requirements-testing.pip ]
        then
            pkg/pip_install_requirements.sh --testing --use-leap-wheels
        fi
        """
    install = "python setup.py develop"

    workdir = repo_name
    sandbox_path = {'PATH':  "../" + venv_name + '/bin/' + ':${PATH}'}
    sandbox_path_soledad = {
        'PATH':  "../../" + venv_name + '/bin/' + ':${PATH}'}
    repo_url = github_repo_url(repo_name)

    factory.addStep(
	steps.Git(repourl=repo_url, codebase=repo_name, clobberOnFailure=True,
                  method='fresh', branch='develop', alwaysUseLatest=True,
		  workdir=workdir))

    #factory.addStep(
    #    steps.Git(repourl=repo_url, branch=git_branch, workdir=workdir,
    #        codebase=repo_name, mode='full', method='clobber',
    #        shallow=True, haltOnFailure=True, name="PullStep... " + repo_url))

    if 'bitmask_client' in repo_name:
        factory.addSteps([
            steps.ShellCommand(command='pkg/postmkvenv.sh', env=sandbox_path,
                         haltOnFailure=False, workdir=workdir,
                         name="postmkenv"),
            steps.ShellCommand(command='make', env=sandbox_path,
                         haltOnFailure=False, workdir=workdir,
                         name="make")
        ])
    if 'soledad.git' in repo_url:
        for subpackage in ["common", "client", "server"]:
            # keymanager doesn't need soledad.server
            if ('keymanager' in venv_name and
                    subpackage is not "server" or
                    'keymanager' is not venv_name):
                factory.addSteps([
                    steps.ShellCommand(
                        command=install_requirements,
                        env=sandbox_path_soledad,
                        haltOnFailure=True,
                        #workdir='build',
		        workdir=workdir+'/'+subpackage,
                        name="reqs: " + repo_name+"."+subpackage),
                    steps.ShellCommand(
                        command=install_requirements_tests,
                        env=sandbox_path_soledad,
                        haltOnFailure=True,
                        workdir=workdir+'/'+subpackage,
			#workdir='build',
                        name="test reqs: " + repo_name+"."+subpackage),
                    steps.ShellCommand(
                        command=install,
                        env=sandbox_path_soledad,
                        haltOnFailure=True,
                        workdir=workdir+'/'+subpackage,
                        #workdir='build',
                        name="Install " + repo_name+"."+subpackage)
                ])
    else:
        factory.addSteps([
            steps.ShellCommand(command=install_requirements, env=sandbox_path,
                         haltOnFailure=False, workdir=workdir,
                         name="reqs: " + repo_name),
            steps.ShellCommand(command=install_requirements_tests,
                         env=sandbox_path, haltOnFailure=False,
                         workdir=workdir, name="test reqs: " + repo_name),
            steps.ShellCommand(command=install, env=sandbox_path,
                         haltOnFailure=True, workdir=workdir,
                         name="Install " + repo_name)
        ])

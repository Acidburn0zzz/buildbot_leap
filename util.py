github_repos_username = 'leapcode'
order_repos_index = 2


def github_repo_url(repo_name):
    return ('git://github.com/' + github_repos_username + '/' + repo_name +
            '.git')

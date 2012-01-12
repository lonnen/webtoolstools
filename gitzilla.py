#!/usr/bin/python
"""
give me a pair of git revisions and a bugzilla target milestone, and I'll show you
the difference.

Example: ./gitzilla.py --target-milestone=2.4 --old-rev=v2.3.5.1 --new-rev=master

Outputs:
'WARNING missing bug message in git log: e9959af'
The sha of a non-merge commit changeset without a bug number.

'OK 701255 in git is in target milestone 2.4'
A commit message with that bug number is in the changeset and that bug is targeted at the supplied milestone

'WARNING 701255 is in target milestone 2.4 but not in git'
That bug number is listed in the milestone but is not in the change set. It may not have landed,
but if the bug is marked resolved fixed check to see if the bug number was left out of the commit message
or if it was landed on the wrong branch.

'WARNING 701255 is only in old rev, and may not be in the new rev'
A commit message with that bug number is in the old-rev, but not the new-rev. If the revs are different
branches the change probably only landed on the old-rev and not the new rev.

'ERROR 701255 is in git but not in target milestone 2.4'
A commit message with that bug number is in the changeset but the bug is not targeted at the supplied milestone.
Check the bug to see if it's mistargeted. Also check that the commit wasn't accidentally reapplied.
"""

import re
import sys
import optparse
import urllib2
import csv
import subprocess

bug_pattern = re.compile(r'bug\s?\d+', flags=re.IGNORECASE)
bz_baseurl = 'https://bugzilla.mozilla.org/buglist.cgi?query_format=advanced&target_milestone=%s&product=Socorro&ctype=csv'

def compare(git_bug_nums, target_milestone):
    bz_url = bz_baseurl % target_milestone

    bug_reports = csv.DictReader(urllib2.urlopen(bz_url))
    bz_bug_nums = set(x['bug_id'] for x in bug_reports)

    for num in (git_bug_nums & bz_bug_nums):
        print 'OK %s in git is in target milestone %s' % (num, target_milestone)

    for num in (bz_bug_nums - git_bug_nums):
        print 'WARNING %s is in target milestone %s but not in git' % (num, target_milestone)

    for num in (git_bug_nums - bz_bug_nums):
        print 'ERROR %s is in git but not in target milestone %s' % (num, target_milestone)

def main(target_milestone, old_rev, new_rev):
    in_new = gitbugs(old_rev, new_rev)
    in_old = gitbugs(new_rev, old_rev)
    only_new = in_new - in_old

    for num in (in_old - in_new):
        print 'WARNING %s is only in old rev, and may not be in the new rev' % (num)

    compare(only_new, target_milestone)

def gitbugs(from_rev, to_rev):
    git_log_args = ['git', 'log', '--oneline', '%s..%s' % (from_rev, to_rev)]
    print 'Running: %s' % ' '.join(git_log_args)
    process = subprocess.Popen(git_log_args, stdout=subprocess.PIPE)
    process.wait()
    if process.returncode != 0:
        print 'git exited non-zero: %s' % process.returncode
        sys.exit(1)

    git_bugs = set()
    for line in process.stdout:
        commit_msg = line.strip()
        bug_msg = bug_pattern.findall(commit_msg)
        if bug_msg == []:
            if 'Merge' not in commit_msg:
                print 'WARNING missing bug message in git log: %s' % commit_msg.split(' ')[0]
        else:
            git_bugs = git_bugs.union(
              set(x.lower().split('bug')[1].strip() for x in bug_msg))

    return git_bugs

if __name__ == '__main__':
    usage = "%prog [options] args_for_git_log"
    parser = optparse.OptionParser("%s\n%s" % (usage.strip(), __doc__.strip()))
    parser.add_option('-t', '--target-milestone', dest='target_milestone',
                      type='string', help='target_milestone to check on bz')
    parser.add_option('-o', '--old-rev', dest='old_rev',
                      type='string', help='old git revision')
    parser.add_option('-n', '--new-rev', dest='new_rev',
                      type='string', help='new git revision')
    (options, args) = parser.parse_args()

    mandatories = ['target_milestone', 'old_rev', 'new_rev']
    for m in mandatories:
        if not options.__dict__[m]:
            print "mandatory option is missing\n"
            parser.print_help()
            sys.exit(-1)

    main(options.target_milestone, options.old_rev, options.new_rev)

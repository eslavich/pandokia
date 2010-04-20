#
# pandokia - a test reporting and execution system
# Copyright 2009, Association of Universities for Research in Astronomy (AURA) 
#

# This program reads this format from STDIN:
#
# project,prefix,contact
#
# There are commas between fields because there are blank fields sometimes.
# project is the project name
# prefix is the name of a prefix
# contact is the email address of a contact
#
# There can be multiple lines for each project/prefix.
#

import pandokia.common as common
import sys

debug = 0

def run () :
    db = common.open_db()

    prev_project = None

    # read all the lines and then sort them.  this ensures that
    # all lines related to a single project are together.
    ll = [ ] 
    for line in sys.stdin :
        ll.append(line)

    ll.sort()

    # iterate over the sorted lines

    for line in ll :
        line = line.strip().split(",")
        if debug :
            print "LINE=",line
        project = line[0]
        prefix = line[1]
        email = line[2]

        if project != prev_project :
            # commit when we move on to the next project
            db.commit()
            # When we start a project, purge all the entries from the table.
            # We then construct all the entries for that project.
            if debug :
                print "DELETE ", project
            db.execute("DELETE FROM contact WHERE project = ?",(project,))
            prev_project = project

        if email == '' :
            # if email is blank, there is nothing useful to insert.  We still wanted
            # to clear the project from the table, though.
            continue

        # find all the tests that match the prefix; write a record for each of them
        if debug :
            print "QUERY PREFIX",prefix
        c = db.execute("SELECT DISTINCT test_name FROM expected WHERE project = ? AND test_name GLOB ?",(project,prefix+"*"))
        for test_name in c :
            ( test_name, ) = test_name
            if debug :
                print "INSERT ",project, test_name, email
            db.execute("INSERT INTO contact ( project, test_name, email ) VALUES ( ?, ?, ? )", (project, test_name, email) )

    db.commit()

    db.close()

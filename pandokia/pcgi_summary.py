#
# pandokia - a test reporting and execution system
# Copyright 2009, Association of Universities for Research in Astronomy (AURA) 
#

import sys
import cgi
import re
import copy
import time

import pandokia.text_table as text_table

import urllib
import pandokia.pcgi
import common

#
#
#

def run ( ) :

    print "content-type: text/html\n\n"

    form = pandokia.pcgi.form
    output = sys.stdout

    db = common.open_db()
    qdb = common.open_qdb()

    #
    # gather up all the expected parameters
    #

    if form.has_key("qid") :
        qid = int( form["qid"].value )
    else :
        qid = ""
        

    if form.has_key("cmp_run") :
        cmp_run = form["cmp_run"].value
        if cmp_run == '' :
            cmp_run = 'daily_yesterday'
        cmp_run = common.find_test_run(cmp_run)
    else :
        cmp_run = ''

    cmptype = 'c'
    if form.has_key("submit") :
        x = form['submit'].value
        if x == 'same' :
            cmptype = 's'
        elif x == 'different' :
            cmptype = 'd'

    show_attr = 0
    if form.has_key("show_attr") :
        show_attr = int(form["show_attr"].value)

    #
    # main heading
    #

    output.write("<h1>Test summary</h1>")

    # generate a link to click on to sort.  use sort_link+"thing" to sort
    # on thing.  thing must be "+xyz" or "-xyz" to sort on column xyz
    # either ascending or descending.
    #
    sort_query = { }
    for x in form :
        if x != 'sort' and x != 'query' :
            sort_query[x] = form[x].value
    sort_link = common.selflink( sort_query, 'summary' ) + "&sort="

    # Sorting is a little weak right now.  We only generate links to sort
    # ascending, and we don't draw little arrows or anything.  We really
    # need for text_table to offer html text for the column heading
    # instead of just link text.

    # 
    #  Offer to compare to a previous run
    #
    # should we make clickable links of other runs or a drop list?  It
    # would be nice, but I discoverd that finding the list would slow 
    # this cgi a _lot_
    output.write("""
Compare to:
<form action=%s>
<input type=hidden name=qid value='%d'>
<input type=hidden name=show_attr value='%d'>
<input type=hidden name=query value='summary'>
<input type=text name=cmp_run value='%s'>
<br>
<input type=submit name=submit value='compare'>
<input type=submit name=submit value='same'>
<input type=submit name=submit value='different'>
</form>
""" % ( pandokia.pcgi.cginame, qid, show_attr, cgi.escape(cmp_run) ) )

    # 
    output.write("""
<form action=%s>
<input type=hidden name=qid value=%d>
<input type=hidden name=show_attr value=1>
<input type=hidden name=query value=summary>
<input type=hidden name=cmp_run value='%s'>
<input type=submit name=submit value='Add Attributes'>
</form>
""" % ( pandokia.pcgi.cginame, qid, cgi.escape(cmp_run) ) )


    #if cmp_run != '' :
    #    output.write("<h3>Compare to: "+cgi.escape(cmp_run)+"</h3>")

    result_table=text_table.text_table()
    result_table.set_html_table_attributes("border=1")

    tda_table = text_table.text_table()
    tda_table.set_html_table_attributes("border=1")

    tra_table = text_table.text_table()
    tra_table.set_html_table_attributes("border=1")

    #
    # this query finds all the test results that are an interesting part of this request
    #

    qdb.execute("UPDATE query_id SET time = ? WHERE qid = ?", (time.time(), qid) )
    c = qdb.execute("SELECT key_id FROM query WHERE qid = ?", (qid,) )

    result_table.define_column("test_run",  link=sort_link+"+test_run")
    result_table.define_column("project",   link=sort_link+"+project")
    result_table.define_column("host",      link=sort_link+"+host")
    result_table.define_column("test_name", link=sort_link+"+test_name")
    result_table.define_column("contact",   link=sort_link+"+contact")
    if cmp_run != "" :
        result_table.define_column("diff",  link=sort_link+"+diff")
        result_table.define_column("other", link=sort_link+"+other")

    result_table.define_column("stat",      link=sort_link+"+stat")

    # these are used to suppress a column when all the results are the same
    all_test_run = { }
    all_project = { }
    all_host = { }

    different = 0
    rowcount = 0
    for x in c :
        ( key_id, ) = x

        #
        # find the result of this test
        #

        c1 = db.execute("SELECT test_run, project, host, test_name, status FROM result_scalar WHERE key_id = ? ", (key_id,) )

        y = c1.fetchone()   # unique index

        if y is None :
            # this can only happen if somebody deletes tests from the database after we populate the qid
            continue

        (test_run, project, host, test_name, status) = y

        # if we are comparing to another run, find the other one; 
        # suppress lines that are different - should be optional
        if cmp_run != "" :
            c2 = db.execute("SELECT status, key_id FROM result_scalar WHERE test_run = ? AND project = ? and host = ? and test_name = ?",
                ( cmp_run, project, host, test_name ) )
            other_status = c2.fetchone()   # unique index
            if other_status is None :
                pass
            else :
                (other_status, other_key_id) = other_status
                # if the other one is the same, go to next row
                if other_status == status :
                    if cmptype == 'd' :
                        continue
                else :
                    if cmptype == 's' :
                        continue
                    result_table.set_value(rowcount, "diff", text=">")
                other_link = common.selflink( { 'key_id' : other_key_id }, linkmode="detail")
                if other_status == "P" :
                    result_table.set_value(rowcount,"other",other_status, link=other_link)
                else :
                    result_table.set_value(rowcount,"other",other_status, html="<font color=red>"+str(other_status)+"</font>", link=other_link)
                result_table.set_html_cell_attributes(rowcount,"other","bgcolor=lightgray")
                if other_status != status :
                    different = different + 1

        all_test_run[test_run] = 1
        all_project[project] = 1
        all_host[host] = 1

        if 0 :
            detail_query = { "test_run" : test_run, "project" : project, "host" : host, "test_name" : test_name }
        else :
            detail_query = { "key_id" : key_id }
        result_table.set_value(rowcount,"test_run",test_run)
        result_table.set_value(rowcount,"project",project)
        result_table.set_value(rowcount,"host",host)
        this_link = common.selflink(detail_query, linkmode="detail")
        result_table.set_value(rowcount,"test_name",text=test_name, link=this_link )

        result_table.set_value(rowcount,"contact",common.get_contact(project, test_name, 'str'))

        if status == "P" :
            result_table.set_value(rowcount,"stat",status, link=this_link)
        else :
            result_table.set_value(rowcount,"stat",status, html="<font color=red>"+str(status)+"</font>", link=this_link)

        if show_attr :
            c3 = db.execute("SELECT name, value FROM result_tda WHERE key_id = ?", ( key_id, ) )
            load_in_table( tda_table, rowcount, c3, "tda_", sort_link )
            del c3

            c3 = db.execute("SELECT name, value FROM result_tra WHERE key_id = ?", ( key_id, ) )
            load_in_table( tra_table, rowcount, c3, "tra_", sort_link )
            del c3


        rowcount += 1

        del c1

    if show_attr:
        result_table.join(tda_table)
        result_table.join(tra_table)

    if len(all_test_run) == 1 :
        result_table.suppress("test_run")
        output.write("<h3>test_run: "+cgi.escape([tmp for tmp in all_test_run][0])+"</h3>")
    if len(all_project) == 1 :
        result_table.suppress("project")
        output.write("<h3>project: "+cgi.escape([tmp for tmp in all_project][0])+"</h3>")
    if len(all_host) == 1 :
        result_table.suppress("host")
        output.write("<h3>host: "+cgi.escape([tmp for tmp in all_host][0])+"</h3>")


    # try to suppress attribute columns where all the data values are the same
    global any_attr
    any_attr = list(any_attr)
    any_attr.sort()

    same_table =text_table.text_table()
    same_table.set_html_table_attributes("border=1")
    same_row = 0

    for x in any_attr :
        all_same = 1
        txt = result_table._row_col_cell(0,x).text
        for y in range(1, rowcount) :
            ntxt = result_table._row_col_cell(y,x).text
            if txt != ntxt :
                all_same = 0
                break

        if all_same :
            same_table.set_value(same_row,0,x)
            same_table.set_value(same_row,1,txt)
            same_row = same_row + 1
            result_table.suppress(x)

    if same_row > 0 :
        output.write( "<ul><b>attributes same for all rows:</b>" )
        output.write( same_table.get_html() )
        output.write( "</ul><br>" )

    
    if form.has_key("sort") :
        sort_order = form["sort"].value
    else :
        sort_order = '+test_name'

    reverse_val = sort_order.startswith("-")

    result_table.set_sort_key( sort_order[1:], float )

    result_table.sort([ sort_order[1:] ], reverse=reverse_val)
    
    output.write(result_table.get_html(color_rows=5))

    output.write( "<br>rows: %d <br>"%rowcount )
    if cmp_run != "" :
        output.write( "different: %d <br>"%different )

    qdict = { "qid" : qid }
    output.write( "<a href='"+common.selflink(qdict, linkmode = "detail")+"'>" )
    output.write( "detail of all</a>" )

any_attr = { }

def load_in_table( tt, row, cursor, prefix, sort_link ) :
    for x in cursor :
        ( name, value ) = x
        name = prefix + name
        tt.define_column(name,link=sort_link+"+"+name)
        tt.set_value(row, name, value)
        any_attr[name]=1

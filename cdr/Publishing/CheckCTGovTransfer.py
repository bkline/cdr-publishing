#!d:/python/python.exe
# *********************************************************************
#
# File Name: $RCSFile:$
#            ===============
# Program to identify and notify about protocols that need to be 
# transferred from PDQ to CTGov.
# ---------------------------------------------------------------------
# $Author: venglisc $
# Created:          2009-03-17        Volker Englisch
# Last Modified:    $
# 
# $Source: /usr/local/cvsroot/cdr/Publishing/CheckCTGovTransfer.py,v $
# $Revision: 1.9 $
#
# $Id: CheckCTGovTransfer.py,v 1.9 2009-09-17 14:52:40 venglisc Exp $
# $Log: not supported by cvs2svn $
# Revision 1.8  2009/09/16 19:22:02  venglisc
# Modified SQL query to also pick up protocols without transfer date.
# (Bug 4638)
#
# Revision 1.7  2009/09/04 21:48:57  venglisc
# Modified program to submit an error message in case the unicode convertion
# failed when writing to file and if the SQL query fails due to a DB timeout.
# (Bug 4633)
#
# Revision 1.6  2009/07/24 20:18:35  venglisc
# Modified the email message to be converted to UTF-8. (Bug 4611)
#
# Revision 1.5  2009/07/24 18:50:25  venglisc
# Modified SQL query to only display primary lead org information. (Bug 4529)
#
# Revision 1.4  2009/05/14 15:20:49  venglisc
# Modified SQL query to remove mandatory Comment from a record. (Bug 4529)
#
# Revision 1.3  2009/05/12 22:35:39  venglisc
# Changed the email body to a Unicode string.
#
# Revision 1.2  2009/05/12 22:10:48  venglisc
# The SQL query frequently timed out.  Increasing timeout value. (Bug 4529)
#
# Revision 1.1  2009/03/27 20:38:12  venglisc
# New email notification to NLM for ownership transferring to responsible
# party. (Bug 4529)
#
# *********************************************************************
import sys, cdr, cdrdb, os, time, optparse, smtplib, glob

OUTPUTBASE     = cdr.BASEDIR + "/Output/CTGovTransfer"
DOC_FILE       = "CTGovTransfer"
LOGNAME        = "CTGovTransfer.log"
SMTP_RELAY     = "MAILFWD.NIH.GOV"
STR_FROM       = "PDQ Operator <operator@cips.nci.nih.gov>"

now            = time.localtime()
outputFile     = '%s_%s.txt' % (DOC_FILE, time.strftime("%Y%m%d%H%M%S", now))

testMode       = None
emailMode      = None

# Create an exception allowing us to break out if there are no new
# protocols found to report.
# ----------------------------------------------------------------
class NoNewDocumentsError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)
class NothingFoundError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

# ------------------------------------------------------------
# Function to parse the command line arguments
# ------------------------------------------------------------
def parseArguments(args):
    """
    Assign all input parameters to variables and perform some error
    checking.
    """

    usage = "usage: %prog [--livemode | --testmode] [options]"
    parser = optparse.OptionParser(usage = usage)

    parser.set_defaults(testMode = True)
    parser.set_defaults(emailMode = True)
    parser.add_option('-t', '--testmode',
                      action = 'store_true', dest = 'testMode',
                      help = 'running in TEST mode')
    parser.add_option('-l', '--livemode',
                      action = 'store_false', dest = 'testMode',
                      help = 'running in LIVE mode')
    parser.add_option('-e', '--email',
                      action = 'store_true', dest = 'emailMode',
                      help = 'running in EMAIL mode')
    parser.add_option('-n', '--noemail',
                      action = 'store_false', dest = 'emailMode',
                      help = 'running in NOEMAIL mode')
    parser.add_option('-f', '--filename',
                      action = 'store', dest = 'file',
                      help = 'run diff on this file')

    # Exit if no command line argument has been specified
    # ---------------------------------------------------
    if len(args[1:]) == 0:
        parser.print_help()
        sys.exit('No arguments given!')

    (options, args) = parser.parse_args()

    # Read and process options, if any
    # --------------------------------
    if parser.values.testMode:
        l.write("Running in TEST mode", stdout = True)
    else:
        l.write("Running in LIVE mode", stdout = True)

    if parser.values.emailMode:
        l.write("Running in EMAIL mode", stdout = True)
    else:
        l.write("Running in NOEMAIL mode", stdout = True)

    if parser.values.file:
        file = parser.values.file
        l.write("Comparing output to file: %s" % file, stdout = True)

    return parser


# ---------------------------------------------------------------------
# Selecting the protocol list created last time this program ran
# ---------------------------------------------------------------------
def getLastProtocolList(directory = cdr.BASEDIR + '/Output/CTGovTransfer'):
    os.chdir(directory)
    if testMode:
        searchFor = '*.test.txt'
    else:
        searchFor = 'CTGovTransfer_??????????????.txt'

    fileList = glob.glob(searchFor)
    if not fileList: return
    fileList.sort()
    fileList.reverse()
    return (fileList[0])
    

# --------------------------------------------------------------------
# Module to submit an email message if the program fails
# --------------------------------------------------------------------
def sendErrorMessage(msg):
    # We want to send an email so that the query doesn't silently fail
    # ----------------------------------------------------------------
    mailHeader   = """\
From: %s
To: %s
Subject: %s: %s
""" % (STR_FROM, '***REMOVED***', cdr.PUB_NAME.capitalize(),
       '*** Error: Program CheckCTGovTransfer failed!')

    mailHeader   += "Content-type: text/html; charset=utf-8\n"
    mailBody      = "<b>Error running CheckCTGovTransfer.py</b><br>"
    mailBody     += "Most likely %s<br>" % msg
    mailBody     += "See log file for details."

    # Add a Separator line + body
    # ---------------------------
    message = mailHeader + "\n" + mailBody

    server = smtplib.SMTP(SMTP_RELAY)
    server.sendmail(STR_FROM, '***REMOVED***', message.encode('utf-8'))
    server.quit()


# ---------------------------------------------------------------------
# Instantiate the Log class
# ---------------------------------------------------------------------
l   = cdr.Log(LOGNAME)
l.write("CTGovTransfer - Started", stdout = True)
l.write('Arguments: %s' % sys.argv, stdout=True)
print ''

options   = parseArguments(sys.argv)
testMode  = options.values.testMode
emailMode = options.values.emailMode

# If no file name is specified (the default) we're picking the last
# file created.
# -----------------------------------------------------------------
if options.values.file:
    useFile = options.values.file
    oldFile = getLastProtocolList(OUTPUTBASE)
    l.write("  Last protocol list was: %s" % oldFile, stdout = True)
else:
    useFile = getLastProtocolList(OUTPUTBASE)
    l.write("Comparing output to file: %s" % useFile, stdout = True)

if testMode:
    outputFile = outputFile.replace('.txt', '.test.txt')

path = OUTPUTBASE + '/%s'
l.write("    New protocol list is: %s" % outputFile, stdout = True)
 
try:
    # Open the latest manifest file (or the one specified) and read 
    # the content
    # -------------------------------------------------------------
    protocols = {}
    oldFile = []
    oldIds = []
    # A) If the file name has been passed as a parameter and the file 
    #    doesn't exist, exit.
    # B) If no file exists in the directory this is the first time the 
    #    process is run and we continue
    # --------------------------------------------------------------------
    if options.values.file and not os.access(path % useFile, os.F_OK):
        sys.exit('Invalid File Name: %s' % useFile)
    elif not options.values.file and not os.access(path % useFile, os.F_OK):
        l.write("No files found.  Assuming new directory", stdout = True)
    else:
        f = open(path % useFile, 'r')
        protocols = f.readlines()
        f.close()

        # Read the list of previously published protocols
        # ------------------------------------------------
        for row in protocols:
            oldIds.append(int(row.split('\t')[0]))


    # Connect to the database to get the full list of protocols with
    # the CTGovDuplicate element.
    # --------------------------------------------------------------
    newWithdrawn = []

    conn = cdrdb.connect()
    cursor = conn.cursor()
        
    try:
        cursor.execute("""\
         SELECT q.doc_id as "CDR-ID", qid.value as "Primary ID", 
                nid.value as "NCTID", o.value as "OrgName", 
                t.value as "Transfer Org", q.value as "PRS Name",
                c.value
           FROM query_term q
-- Find the blocked documents (active_status)
--  JOIN document d
--    ON d.id = q.doc_id
-- Get the Primar Protocol ID
           JOIN query_term qid
             ON q.doc_id = qid.doc_id
            AND qid.path = '/InScopeProtocol/ProtocolIds/PrimaryID/IDString'
-- Get Other-ID/NCTID
           JOIN query_term_pub nid
             ON q.doc_id = nid.doc_id
            AND nid.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDString'
           JOIN query_term_pub nt
             ON q.doc_id = nt.doc_id
            AND nt.path = '/InScopeProtocol/ProtocolIDs/OtherID/IDType'
            AND nt.value = 'ClinicalTrials.gov ID'
            AND LEFT(nt.node_loc, 8) = LEFT(nid.node_loc, 8)
-- Get Lead Org ID
           JOIN query_term_pub oid
             ON q.doc_id = oid.doc_id
            AND oid.path = '/InScopeProtocol/ProtocolAdminInfo' + 
                           '/ProtocolLeadOrg/LeadOrganizationID/@cdr:ref'
-- Get Lead Org Name
           JOIN query_term_pub o
             ON oid.int_val = o.doc_id
            AND o.path = '/Organization/OrganizationNameInformation' + 
                         '/OfficialName/Name'
-- Get the primary Lead Org
           JOIN query_term_pub poid
             ON oid.doc_id = poid.doc_id
            AND poid.path  = '/InScopeProtocol/ProtocolAdminInfo'     +
                             '/ProtocolLeadOrg/LeadOrgRole'
            AND poid.value = 'Primary'
            AND left(oid.node_loc, 8) = left(poid.node_loc, 8)

-- Get the Transfer Org Name
           JOIN query_term t
             ON t.doc_id = q.doc_id
            AND t.path = '/InScopeProtocol/CTGovOwnershipTransferInfo' +
                         '/CTGovOwnerOrganization'
-- Get the Ownership Comment
LEFT OUTER JOIN query_term c
             ON c.doc_id = q.doc_id
            AND c.path = '/InScopeProtocol/CTGovOwnershipTransferInfo' +
                           '/Comment'
-- Get the transfer date
--         JOIN query_term prs
--           ON prs.doc_id = q.doc_id
--          AND prs.path = '/InScopeProtocol/CTGovOwnershipTransferInfo' +
--                         '/CTGovOwnershipTransferDate'
-- Get the PRS Name
          where q.path = '/InScopeProtocol/CTGovOwnershipTransferInfo' +
                         '/PRSUserName'
--   and active_status <> 'A'
           ORDER by q.doc_id""", timeout = 300)

        rows = cursor.fetchall()
        cursor.close()
    except cdrdb.Error, info:
        l.write("Failure retrieving protocols: \n%s" % info[1][0], 
                 stdout = True)
        sendErrorMessage('SQL query timeout error')
        raise

    # Create the new manifest file and identify those records that
    # are new since the last time this job ran (by comparing to the
    # file created last time).
    # -------------------------------------------------------------
    f = open(path % outputFile, 'w')
    newIds = []
    l.write("", stdout = True)
    l.write("List of new CTGovTransfer protocols", stdout = True)
    l.write("-----------------------------------",   stdout = True)
    for (cdrId, protocolId, nctId, orgName, transferOrg,
         prsName, comment) in rows:
        # l.write("%s, %s, %s, %s" % (cdrId, protocolId, nctId, orgName), 
        #                             stdout = True)

        try:
            if cdrId not in oldIds:
                l.write("%s, %s, %s, %s" % (cdrId, protocolId, nctId, orgName), 
                                            stdout = True)
                f.write("%10s\t%25s\t%12s\tNew\n" % (cdrId, 
                                                    protocolId.encode('utf-8'), 
                                                    nctId.encode('utf-8')))
                newIds.append(cdrId)
            else:
                f.write("%10s\t%25s\t%12s\n" % (cdrId, 
                                                protocolId.encode('utf-8'), 
                                                nctId.encode('utf-8')))
        except Exception, info:
            l.write("Failure retrieving protocols: \n%s" % info[1][0], 
                     stdout = True)
            sendErrorMessage('writing Unicode convertion error')
            raise

    f.close()

    # Create the message body and display the query results
    # -----------------------------------------------------
    if newIds:
        l.write("", stdout = True)
        l.write('List of transferred protocol IDs', stdout = True)
        l.write('--------------------------------', stdout = True)
        l.write('%s' % newIds, stdout = True)
        mailBody = u"""\
<html>
 <head>
  <title>Transfer Ownership to Responsible Party</title>
  <style type='text/css'>
   th      { background-color: #f0f0f0; }
  </style>
 </head>
 <body>
  <h2>Transfer Ownership to Responsible Party</h2>
  <h3>Date: %s</h3>

  <table border='1px' cellpadding='2px' cellspacing='2px'>
   <tr>
    <th>CDR-ID</th>
    <th>Primary ID</th>
    <th>NCT-ID</th>
    <th>Lead Org Name</th>
    <th>Transfer Org</th>
    <th>PRS Username</th>
    <th>Comment</th>
   </tr>
""" % (time.strftime("%m/%d/%Y", now))

        try:
            for (cdrId, protocolId, nctId, orgName, transOrgName,
                 PRSName, comment) in rows:
                if cdrId in newIds:
                    mailBody += u"""\
   <tr>
    <td>CDR%010d</td>
    <td>%s</td>
    <td>
     <a href="http://www.clinicaltrials.gov/ct2/show/%s">%s</a>
    </td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
    <td>%s</td>
   </tr>
""" % (cdrId, protocolId, nctId, nctId, orgName, transOrgName,
       PRSName, comment)
        except Exception, info:
            l.write("Failure retrieving protocols: \n%s" % info[1][0], 
                     stdout = True)
            sendErrorMessage('Unicode convertion error')
            raise


        mailBody += u"""\
  </table>

 </body>
</html>
"""
    else:
        raise NoNewDocumentsError('NoNewDocumentsError')
        

    # In Testmode we don't want to send the notification to the world
    # ---------------------------------------------------------------
    # Email constants
    # ---------------
    if testMode:
        strTo    = cdr.getEmailList('Test Publishing Notification')
    else:
        strTo    = cdr.getEmailList('CTGov Transfer Notification')
        #strTo.append(u'register@clinicaltrials.gov')

    mailHeader   = """\
From: %s
To: %s
Subject: %s: %s
""" % (STR_FROM, u', '.join(strTo), cdr.PUB_NAME.capitalize(),
       'Transfer of Protocol(s) from NCI to Responsible Party')

    mailHeader   += "Content-type: text/html; charset=utf-8\n"

    # Add a Separator line + body
    # ---------------------------
    message = mailHeader + "\n" + mailBody

    #print message

    # Sending out the email 
    # ---------------------
    server = smtplib.SMTP(SMTP_RELAY)
    if emailMode:
        try:
            server.sendmail(STR_FROM, strTo, message.encode('utf-8'))
        except Exception, info:
            sys.exit("*** Error sending message: %s" % str(info))
    else:
        l.write("Running in NOEMAIL mode.  No message send", stdout = True)
    server.quit()

except NothingFoundError, arg:
    msg  = "No documents found with 'CTGovDuplicate' element"
    l.write("   %s" % msg, stdout = True)
    l.write("   %s" % arg, stdout = True)
except NoNewDocumentsError, arg:
    msg  = "No new documents found with 'CTGovDuplicate' element"
    l.write("", stdout = True)
    l.write("   %s" % msg, stdout = True)
    l.write("   %s" % arg, stdout = True)
except Exception, arg:
    l.write("*** Standard Failure - %s" % arg, stdout = True, tback = 1)
except:
    l.write("*** Error - Program stopped with failure ***", stdout = True, 
                                                            tback = 1)
    raise

l.write("CTGovTransfer - Finished", stdout = True)
sys.exit(0)

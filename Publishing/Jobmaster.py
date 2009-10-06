#!d:/python/python.exe
# *********************************************************************
#
# File Name: Jobmaster.py
#            ===============
# Control file to start the publishing scripts.
# ---------------------------------------------------------------------
# $Author: venglisc $
# Created:          2007-04-03        Volker Englisch
# Last Modified:    $Date: 2009-09-15 17:35:34 $
# 
# $Source: /usr/local/cvsroot/cdr/Publishing/Jobmaster.py,v $
# $Revision: 1.15 $
#
# $Id: Jobmaster.py,v 1.15 2009-09-15 17:35:34 venglisc Exp $
# $Log: not supported by cvs2svn $
# Revision 1.14  2009/03/27 20:13:18  venglisc
# Adding new production steps (Bug 4429, 4497, 4529)
#
# Revision 1.13  2009/02/27 23:28:05  venglisc
# Added new step to run CheckRepublishWithdrawn.py. (Bug 4450)
#
# Revision 1.12  2009/01/23 19:26:19  venglisc
# Added new step to run the Media report for Visual OnLine. (Bug 4402)
#
# Revision 1.11  2008/10/06 19:52:26  venglisc
# Fixed typo in len() function. (Bug 4123)
#
# Revision 1.10  2008/09/26 22:23:35  venglisc
# Including the ArmsCount script in publishing schedule.
#
# Revision 1.9  2008/09/16 18:10:09  venglisc
# Added code to create licensee output from CG output.  The data is then
# revalidated with the pdq.dtd. (Bug 4123)
#
# Revision 1.8  2008/02/19 23:49:19  venglisc
# Fixed directory name format error to identify the directories to be
# checked for CheckWithdrawn.py.
#
# Revision 1.7  2007/12/12 20:41:11  venglisc
# Added additional production step to check the WithdrawnFromPDQ.txt file
# for newly added protocols. (Bug 3761)
#
# Revision 1.6  2007/11/14 19:38:09  venglisc
# Modified program to run the CTGovExport as part of the nightly job
# and push the data to NLM's ftp site.
#
# Revision 1.5  2007/09/07 22:29:53  venglisc
# Removed backup option.
#
# Revision 1.4  2007/08/22 00:50:04  venglisc
# Added code to only run the CTGovExport creation on Wednesdays and
# Fridays per NLM request.
#
# Revision 1.3  2007/08/14 00:04:40  venglisc
# Final version of Jobmaster.py.  For production the NightlyRefresh
# to update the CDR database on FRANCK has been removed.
#
# Revision 1.2  2007/08/10 16:44:37  venglisc
# Finalized initial version of submission program.
#
# Revision 1.1  2007/07/06 16:41:23  venglisc
# Initial copy of Jobmaster script used to run all nightly publishing
# steps for MFP.
#
# *********************************************************************
import sys, re, string, os, shutil, cdr, getopt, time, glob

# Setting directory and file names
# --------------------------------
PUBPATH    = os.path.join('d:\\cdr', 'publishing')
# PUBPATH    = os.path.join('d:\\home', 'venglisch', 'cdr', 'publishing')

UTIL       = os.path.join('d:\\cdr', 'Utilities')
LOGFILE    = 'Jobmaster.log'

weekDay    = time.strftime("%a")
testMode   = None
fullUpdate = None
refresh    = True
istep      = 0

EmailError = 'oops'
CTGovError = 'oops'

# ------------------------------------------------------------
# Function to parse the command line arguments
# Note:  testmode/livemode is currently only used to be passed
#        to the called program
# ------------------------------------------------------------
def parseArgs(args):

    global testMode
    global fullUpdate
    global refresh
    global l

    try:
        longopts = ["testmode", "livemode", "interim", "export"]
        opts, args = getopt.getopt(args[1:], "tlie", longopts)
    except getopt.GetoptError, e:
        usage(args)

    for o, a in opts:
        if o in ("-o", "--logfile"):
            global LOGFILE
            LOGFILE = a
            l = cdr.Log(LOGFILE)
        elif o in ("-t", "--testmode"):
            testMode = True
            l.write("running in TEST mode")
        elif o in ("-l", "--livemode"):
            testMode = False
            l.write("running in LIVE mode")
        elif o in ("-i", "--interim"):
            fullUpdate = False
            l.write("running in INTERIM mode")
        elif o in ("-e", "--export"):
            fullUpdate = True
            l.write("running in EXPORT mode")

    if len(args) > 0:
        usage(args)
    if testMode is None:
        usage(args)
    if fullUpdate is None:
        usage(args)

    return


# ------------------------------------------------------------
# Function to display the default usage
# ------------------------------------------------------------
def usage(args):
    print args
    sys.stderr.write("""\
usage: %s [--livemode|--testmode] [--interim|--export] [options]

options:
    -i, --interim
           running in interim (nightly) production mode

    -e, --export
           running in export (weekly) production mode

    -t, --testmode
           run in TEST mode

    -l, --livemode
           run in LIVE mode

""" % sys.argv[0].split('\\')[-1])
    sys.exit(1)

# ------------------------------------------------------------
# Function to find the directory names storing the CTGovExport
# data.
# The file names are created automatically and represent a 
# time stamp.  Once the CTGovExport job finished we need to 
# identify the newly created directory name plus the one 
# created before this containing the files WithdrawnFromPDQ.txt
# ------------------------------------------------------------
def getCTGovExportDirs(baseDir = "/cdr/Output/NLMExport"):
    """
    Retrieve the directories created by the CTGovExport process
    for the current month and the month before and sort them 
    by date.  We want to compare the latest directory content
    with the one created just before as long as it contains the 
    file WithdrawnFromPDQ.txt
    """
    # Setting variables
    # -----------------
    notPDQ  = 'WithdrawnFromPDQ.txt'
    now     = time.localtime(time.time())
    fromDir = str(now[0]) + '%02d' % (now[1] - 1)
    toDir   = str(now[0]) + '%02d' % now[1]

    # Find the directories created during the past two months
    # -------------------------------------------------------
    dirs1   = glob.glob(baseDir + '/' + fromDir + '*')
    dirs2   = glob.glob(baseDir + '/' + toDir   + '*')
    allDirs = dirs1 + dirs2
    allDirs.sort()
    allDirs.reverse()
    
    # Find the last two directories that contain the 
    # WithdrawnFromPDQ.txt file (not all do)
    # ----------------------------------------------
    checkDirs = ()
    dirCount  = 0
    for dir in allDirs:
        if os.access(dir + '/' + notPDQ , os.F_OK):
            dirCount += 1
            dstart = dir.find('20')      # Change to 21 for year > 2100 
            checkDirs += (dir[dstart:],)
            if dirCount == 2: break

    # If there didn't run any full export jobs during this and the last
    # month, we have nothing to compare and we can't return a tuple
    # -----------------------------------------------------------------
    if len(checkDirs) < 2:
        return None

    return (checkDirs[:2])

    
# ------------------------------------------------------------
# *** Main ***
# Jetzt wird es ernst
# ------------------------------------------------------------

# Open Log file and enter start message
# -------------------------------------
l = cdr.Log(LOGFILE)
l.write('Jobmaster Publishing - Started', stdout = True)
l.write('Arguments: %s' % sys.argv, stdout=True)

parseArgs(sys.argv)

# Setting the options for jobs which we are going to submit
# ---------------------------------------------------------
if testMode:
    runmode = '--testmode'
else:
    runmode = '--livemode'

if fullUpdate:
    pubmode = '--export'
else:
    pubmode = '--interim'


# Submit initial email notification to indicate process has started
# -----------------------------------------------------------------
try:
    istep += 1
    l.write('--------------------------------------------', stdout = True)
    l.write('Step %d: Initial Email' % istep, stdout = True)
    if fullUpdate:
        subject = 'Weekly Publishing Started'
        message = 'Weekly Job Started Successfully'
        cmd     = os.path.join(PUBPATH, 'PubEmail.py "%s" "%s"' % \
                                        (subject, message))
    else:
        subject = 'Nightly Publishing Started'
        message = 'Nightly Job Started Successfully'
        cmd     = os.path.join(PUBPATH, 'PubEmail.py "%s" "%s"' % \
                                        (subject, message))
    l.write('Submitting command...\n%s' % cmd, stdout = True)
    try:
        myCmd = cdr.runCommand(cmd)
        print "Code: ", myCmd.code
        print "Outp: ", myCmd.output.find('Failure')
        print "--------------"
        if myCmd.code or myCmd.output.find('Failure') > 0:
            raise EmailError
    except EmailError:
        l.write('*** Error submitting email\n%s' % myCmd.output, 
                 stdout = True)
        raise
except:
    l.write('Sending Initial Email failed', stdout = True)
    sys.exit(1)

try:
    istep += 1
    l.write('--------------------------------------------', stdout = True)
    l.write('Step %d: Submit Pub Job' % istep, stdout = True)
    cmd = os.path.join(PUBPATH, 'SubmitPubJob.py %s %s' % (runmode, pubmode))

    l.write('Submitting command...\n%s' % cmd, stdout = True)

    myCmd = cdr.runCommand(cmd)
    
    print "Code: ", myCmd.code
    print "Outp: ", myCmd.output.find('Failure')
    print "--------------"
    if myCmd.code or myCmd.output.find('Failure') > 0:
        l.write('*** Error submitting command:\n%s' % myCmd.output, 
                 stdout = True)
        subject = '*** Error in SubmitPubJob.py'
        message = 'Program returned with error code.  Please see logfile.'
        cmd     = os.path.join(PUBPATH, 'PubEmail.py "%s" "%s"' % \
                                        (subject, message))
        myCmd   = cdr.runCommand(cmd)
        raise

except:
    l.write('Submitting Publishing Job failed', stdout = True)
    sys.exit(1)

# Process the licensee data that's running on weekends only
# ---------------------------------------------------------
if fullUpdate:

    # FTP the publishing data (Vendor output) to CIPSFTP
    # Note: Step only needed for weekly publishing
    # --------------------------------------------------
    try:
        istep += 1
        l.write('--------------------------------------------', stdout = True)
        l.write('Step %d: CG2Public Job' % istep, stdout = True)
        cmd = os.path.join(PUBPATH, 'CG2Public.py %s %s' % (runmode, pubmode)) 

        l.write('Submitting command...\n%s' % cmd, stdout = True)
        myCmd = cdr.runCommand(cmd)

        if myCmd.code:
            l.write('*** Error submitting command:\n%s' % myCmd.output,
                     stdout = True)
            l.write('Code: %s' % myCmd.code, stdout = True)
            subject = '*** Error in CG2Public.py'
            message = 'Program returned with error code.  Please see logfile.'
            cmd     = os.path.join(PUBPATH, 'PubEmail.py "%s" "%s"' % \
                                        (subject, message))
            myCmd   = cdr.runCommand(cmd)
            raise
    except:
        l.write('Submitting CG2Public Job failed', stdout = True)
        sys.exit(1)

    # FTP the publishing data (Vendor output) to CIPSFTP
    # Note: Step only needed for weekly publishing
    # --------------------------------------------------
    try:
        istep += 1
        l.write('--------------------------------------------', stdout = True)
        l.write('Step %d: FtpExportData Job' % istep, stdout = True)
        cmd = os.path.join(PUBPATH, 'FtpExportData.py %s %s' % (runmode, 
                                                                pubmode)) 

        l.write('Submitting command...\n%s' % cmd, stdout = True)
        myCmd = cdr.runCommand(cmd)

        if myCmd.code:
            l.write('*** Error submitting command:\n%s' % myCmd.output,
                     stdout = True)
            l.write('Code: %s' % myCmd.code, stdout = True)
            subject = '*** Error in FtpExportData.py'
            message = 'Program returned with error code.  Please see logfile.'
            cmd     = os.path.join(PUBPATH, 'PubEmail.py "%s" "%s"' % \
                                        (subject, message))
            myCmd   = cdr.runCommand(cmd)
            raise
    except:
        l.write('Submitting FtpExportData Job failed', stdout = True)
        sys.exit(1)


# FTP the NCICB Terminolofy data to CIPSFTP
# This data contains an extra element not intended for licensees
# Note: Step only needed for weekly publishing
# Note: As of 2009-09-13 the NCICB data should be transferred
#       nightly.
# --------------------------------------------------------------
try:
    istep += 1
    l.write('--------------------------------------------', stdout = True)
    l.write('Step %d: FtpOtherData Job' % istep, stdout = True)
    cmd = os.path.join(PUBPATH, 'FtpOtherData.py %s %s' % (runmode, 
                                                            pubmode)) 

    l.write('Submitting command...\n%s' % cmd, stdout = True)
    myCmd = cdr.runCommand(cmd)

    if myCmd.code:
        l.write('*** Error submitting command:\n%s' % myCmd.output,
                 stdout = True)
        l.write('Code: %s' % myCmd.code, stdout = True)
        subject = '*** Error in FtpOtherData.py'
        message = 'Program returned with error code.  Please see logfile.'
        cmd     = os.path.join(PUBPATH, 'PubEmail.py "%s" "%s"' % \
                                    (subject, message))
        myCmd   = cdr.runCommand(cmd)
        raise
except:
    l.write('Submitting FtpOtherData Job failed', stdout = True)
    sys.exit(1)


# Create the CTGovExport data with every nightly job and the full export
# as part of the weekly (on Friday/Saturday).
# -------------------------------------------------------------------
# Create the CTGovExport data for NLM
# -----------------------------------
try:
    istep += 1
    l.write('--------------------------------------------', stdout = True)
    l.write('Step %d: CTGovExport Job' % istep, stdout = True)

    if fullUpdate:
        since = '--since="2000-01-01"'
        cmd = os.path.join(UTIL, 
                           'CTGovExport.py --optimize %s %s' %  (runmode,
                                                                 since))
                        ###'CTGovExport.py            %s %s' %  (runmode,
                        ###'CTGovExport.py --optimize %s %s' %  (runmode,
    else:
        cmd = os.path.join(UTIL, 
                           'CTGovExport.py --optimize %s' %  runmode)
                         # 'CTGovExport.py --optimize --maxtest 100 %s' %  
                         #                                         runmode)
                         #   Specifying maxtest option for testing only
    
    l.write('Submitting CTGovExport Job...\n%s' % cmd, stdout = True)
    myCmd = cdr.runCommand(cmd)
    
    if myCmd.code:
        l.write('*** Error submitting command:\n%s' % myCmd.output,
                 stdout = True)
        subject = '*** Error in CTGovExport.py'
        message = 'Program returned with error code.  Please see logfile.'
        cmd     = os.path.join(PUBPATH, 'PubEmail.py "%s" "%s"' % \
                                        (subject, message))
        myCmd   = cdr.runCommand(cmd)
        raise
except:
    l.write('Submitting CTGovExport Job failed', stdout = True)
    sys.exit(1)
    
    
# Ftp the FtpCTGovData to the CIPSFTP server
# ------------------------------------------
try:
    istep += 1
    l.write('--------------------------------------------', stdout = True)
    l.write('Step %d: FTP CTGov2Nlm Job' % istep, stdout = True)
    cmd = os.path.join(PUBPATH, 'FtpCTGov2Nlm.py %s' % runmode)
    
    l.write('Submitting command...\n%s' % cmd, stdout = True)
    myCmd = cdr.runCommand(cmd)
    
    if myCmd.code:
        l.write('*** Error submitting command:\n%s' % myCmd.output,
                 stdout = True)
        subject = '*** Error in FtpCTGov2Nlm.py'
        message = 'Program returned with error code.  Please see logfile.'
        cmd = os.path.join(PUBPATH, 'PubEmail.py "%s" "%s"' % \
                                    (subject, message))
        myCmd = cdr.runCommand(cmd)
        raise
except:
    l.write('Submitting FtpCTGov2Nlm Job failed', stdout = True)
    sys.exit(1)


# Check for new protocols with status 'Withdrawn from PDQ'
# --------------------------------------------------------
try:
    istep += 1
    l.write('--------------------------------------------', stdout = True)
    l.write('Step %d: Submitting CheckWithdrawn Job' % istep, stdout = True)
    dirs = getCTGovExportDirs()

    if type(dirs) == type(()):
        cmd = os.path.join(PUBPATH, 
                       'CheckWithdrawn.py "%s" "--dir=%s" "--dir=%s"' % \
                                               (runmode, dirs[0], dirs[1]))
    
        l.write('Submitting command...\n%s' % cmd, stdout = True)
        myCmd = cdr.runCommand(cmd)
    
        if myCmd.code:
            l.write('*** Error submitting command:\n%s' % myCmd.output,
                 stdout = True)
            subject = '*** Error in CheckWithdrawn.py'
            message = 'Program returned with error code.  Please see logfile.'
            cmd = os.path.join(PUBPATH, 'PubEmail.py "%s" "%s"' \
                                    (subject, message))
            myCmd = cdr.runCommand(cmd)
            raise
    else:
        l.write('*** Warning: Unable to submit CheckWithdrawn.py',
                 stdout = True)
        l.write('             Nothing to compare to!',
                 stdout = True)
except StandardError, info:
    l.write('Submitting CheckWithdrawn Job failed\n%s' % str(info), 
                                                         stdout = True)
    sys.exit(1)


# Check for protocols that were re-activated (i.e. published, 
# then withdrawn, and now published again).
# -----------------------------------------------------------
try:
    istep += 1
    l.write('--------------------------------------------', stdout = True)
    l.write('Step %d: Submitting CheckRepublishWithdrawn Job' % istep, 
                                                            stdout = True)
    cmd = os.path.join(PUBPATH, 'CheckRepublishWithdrawn.py "%s"' % \
                                                                runmode)
    
    l.write('Submitting command...\n%s' % cmd, stdout = True)
    myCmd = cdr.runCommand(cmd)
    
    if myCmd.code:
        l.write('*** Error submitting command:\n%s' % myCmd.output,
             stdout = True)
        subject = '*** Error in CheckRepublishWithdrawn.py'
        message = 'Program returned with error code.  Please see logfile.'
        cmd = os.path.join(PUBPATH, 'PubEmail.py "%s" "%s"' % \
                                                       (subject, message))
        myCmd = cdr.runCommand(cmd)
        raise
except StandardError, info:
    l.write('Submitting CheckRepublishWithdrawn Job failed\n%s' % str(info), 
                                                         stdout = True)
    sys.exit(1)


# Check for protocols with the CTGovDuplicate flag
# --------------------------------------------------------
try:
    istep += 1
    l.write('--------------------------------------------', stdout = True)
    l.write('Step %d: Submitting CheckCTGovDuplicate Job' % istep, 
                                                            stdout = True)
    cmd = os.path.join(PUBPATH, 'CheckCTGovDuplicate.py "%s"' % runmode)
    
    l.write('Submitting command...\n%s' % cmd, stdout = True)
    myCmd = cdr.runCommand(cmd)
    
    if myCmd.code:
        l.write('*** Error submitting command:\n%s' % myCmd.output,
             stdout = True)
        subject = '*** Error in CheckCTGovDuplicate.py'
        message = 'Program returned with error code.  Please see logfile.'
        cmd = os.path.join(PUBPATH, 'PubEmail.py "%s" "%s"' % \
                                                     (subject, message))
        myCmd = cdr.runCommand(cmd)
        raise
except StandardError, info:
    l.write('Submitting CheckCTGovDuplicate Job failed\n%s' % str(info), 
                                                         stdout = True)
    sys.exit(1)



# Check for protocols that have been transferred to the 
# respective responsible party and will soon be blocked on PDQ
# ------------------------------------------------------------
try:
    istep += 1
    l.write('--------------------------------------------', stdout = True)
    l.write('Step %d: Submitting CheckCTGovTransfer Job' % istep, 
                                                            stdout = True)
    cmd = os.path.join(PUBPATH, 'CheckCTGovTransfer.py "%s"' % \
                                                                runmode)
    
    l.write('Submitting command...\n%s' % cmd, stdout = True)
    myCmd = cdr.runCommand(cmd)
    
    if myCmd.code:
        l.write('*** Error submitting command:\n%s' % myCmd.output,
             stdout = True)
        subject = '*** Error in CheckCTGovTransfer.py'
        message = 'Program returned with error code.  Please see logfile.'
        cmd = os.path.join(PUBPATH, 'PubEmail.py "%s" "%s"' % \
                                                       (subject, message))
        myCmd = cdr.runCommand(cmd)
        raise
except StandardError, info:
    l.write('Submitting CheckCTGovTransfer Job failed\n%s' % str(info), 
                                                         stdout = True)
    sys.exit(1)



if fullUpdate:
    # Submit the job to count the # of studies with Arms info
    # Note: Step only needed for weekly publishing
    # -------------------------------------------------------
    try:
        istep += 1
        l.write('--------------------------------------------', stdout = True)
        l.write('Step %d: CountArmsLabel Job' % istep, stdout = True)
        cmd = os.path.join(UTIL, 'CountArmsLabel.py %s' % (runmode)) 

        l.write('Submitting command...\n%s' % cmd, stdout = True)
        myCmd = cdr.runCommand(cmd)

        if myCmd.code:
            l.write('*** Error submitting command:\n%s' % myCmd.output,
                     stdout = True)
            l.write('Code: %s' % myCmd.code, stdout = True)
            subject = '*** Error in CountArmsLabel.py'
            message = 'Program returned with error code.  Please see logfile.'
            cmd     = os.path.join(PUBPATH, 'PubEmail.py "%s" "%s"' % \
                                        (subject, message))
            myCmd   = cdr.runCommand(cmd)
            raise
    except:
        l.write('Submitting CountArmsLabel Job failed', stdout = True)
        sys.exit(1)


    # Submit the job to check for newly published media 
    # documents and send a notification email
    # Note: Step only needed for weekly publishing
    # -------------------------------------------------------
    try:
        istep += 1
        l.write('--------------------------------------------', stdout = True)
        l.write('Step %d: Notify_VOL Job' % istep, stdout = True)
        cmd = os.path.join(PUBPATH, 'Notify_VOL.py %s' % (runmode)) 

        l.write('Submitting command...\n%s' % cmd, stdout = True)
        myCmd = cdr.runCommand(cmd)

        if myCmd.code:
            l.write('*** Error submitting command:\n%s' % myCmd.output,
                     stdout = True)
            l.write('Code: %s' % myCmd.code, stdout = True)
            subject = '*** Error in Notify_VOL.py'
            message = 'Program returned with error code.  Please see logfile.'
            cmd     = os.path.join(PUBPATH, 'PubEmail.py "%s" "%s"' % \
                                        (subject, message))
            myCmd   = cdr.runCommand(cmd)
            raise
    except:
        l.write('Submitting Notify_VOL Job failed', stdout = True)
        sys.exit(1)




# Send final Notification that publishing on CDR servers has finished
# Note: More processing to be completed on Cancer.gov and CIPSFTP
# -------------------------------------------------------------------
try:
    istep += 1
    l.write('--------------------------------------------', stdout = True)
    l.write('Step %d: Jobmaster Job Complete notification' % istep, 
                                                           stdout = True)
    if fullUpdate:
        subject = 'Weekly Publishing Finished'
        message = 'Weekly Job Finished Successfully'
        cmd = os.path.join(PUBPATH, 'PubEmail.py "%s" "%s"' % \
                                     (subject, message))
    else:
        subject = 'Nightly Publishing Finished'
        message = 'Nightly Job Finished Successfully'
        cmd = os.path.join(PUBPATH, 'PubEmail.py "%s" "%s"' % \
                                    (subject, message))
    l.write('Submitting command...\n%s' % cmd, stdout = True)
    try:
        myCmd = cdr.runCommand(cmd)
        print "Code: ", myCmd.code
        print "Outp: ", myCmd.output.find('Failure')
        print "--------------"
        if myCmd.code or myCmd.output.find('Failure') > 0:
            raise EmailError
    except EmailError:
        l.write('*** Error submitting email\n%s' % myCmd.output,
                 stdout = True)
        raise
except:
    l.write('Submitting Final Email failed', stdout = True)
    sys.exit(1)

# All done, going home now
# ------------------------
l.write('Jobmaster Publishing - Finished', stdout = True)
sys.exit(0)
#----------------------------------------------------------------------
#
# File Name: FtpInterimDocs.py
# ============================
# Package and submit interim update documents (mid-month updates) to the 
# CIPSFTP server and store files in the directory cdr.
# The documents are located in subdirectories named JobNNN with NNN
# being an integer number.  Provide all jobIDs for the documents that 
# should be packaged within one subdirectory on the FTP server as a
# command line argument.
# For instance, if an interim update ran under JobID=1234 and an
# interim remove ran under JobID=1235 you want to package these 
# documents by entering the command
#     FtpInterimDocs.py 1234 1235
# 
# Once the documents have been packaged and copied to the FTP server 
# there is a post-process that will have to run on the FTP server.
#
# The original name of this program was FtpHotfixDocs.py but got
# renamed after the update process got named 'Interim Update'.
#
# $Id: FtpInterimDocs.py,v 1.4 2008-06-03 21:43:05 bkline Exp $
# $Log: not supported by cvs2svn $
# Revision 1.3  2006/06/14 21:30:10  venglisc
# The FTP process has now been simplified because we are creating a comressed
# tar file from interim update directories to prevent problems in case of a
# large number of documents needing to be pushed.
# The process now allows also to include processing of an entire document
# type interim update.  These files are located within a subdirectory of the
# JobNNNN directory.
# Just specify
#    FtpInterimDocs.py NNNN/ProtocolActive
# for those documents instead of just specifying the Job-ID.
# Mixing of both notations is possible. (Bug 2140)
#
# Revision 1.2  2005/08/05 20:55:53  venglisc
# Replaced the path to the ftp command with SYSTEMROOT variable.
#
# Revision 1.1  2005/07/07 22:03:23  venglisc
# Initial version of FtpInterimDocs.py, however this program was named
# FtpHotfixDocs.py in its former life.  Its name got changed due to the
# renaming of the process from 'Hot Fix Updates' to 'Interim Updates'.
# I changed all references to 'Hot fix' (including the log file name).
#
#----------------------------------------------------------------------
import sys, re, string, cdr, os, shutil, time

if len(sys.argv) < 2:
   sys.stderr.write('usage: FtpInterimDocs jobID[/dirname] [JobID [...]]\n')
   sys.stderr.write(' i.e.: FtpInterimDocs 3388 3389/ProtocolActive 3390\n')
   sys.exit(1)

# Setting directory and file names
# --------------------------------
log      = "d:\\cdr\\log\\interim.log" 
outDir   = 'd:\\' + os.path.join('cdr', 'Output')
pubDir   = 'd:\\' + os.path.join('cdr', 'publishing')
hfDir    = os.path.join(outDir, 'mid-month')
dateStr  = time.strftime("%Y-%m-%d-%H%M", time.localtime())
newDir   = os.path.join(hfDir, dateStr)
manifest = 'media_catalog.txt'
tarName  = dateStr + '.tar.bz2'
rmDir    = 0
cdrDir   = 0

# If the first argument is entered with subdirectory name as in
#   3388/ActiveProtocol we need to strip the subdirectory name
# -------------------------------------------------------------
jobId = string.atoi(sys.argv[1].rsplit('/')[0])
divider = "=" * 60

# ------------------------------------------------------------
# Function to remove duplicate list elements from a given list
# ------------------------------------------------------------
def removeDups(list):
    result = []
    for item in list:
        if item not in result:
            result.append(item)
    return result

# Open Log file and enter start message
# -------------------------------------
open(log, "a").write("Job %d: %s\n    %d: Started at: %s\n" % \
                    (jobId, divider, jobId, time.ctime(time.time())))
try:

    print "Processing files..."
    rmDoc = re.compile('Removed this document')
    mfFiles = []
    for k in sys.argv[1:]:
        oldDir = os.path.join(outDir, 'Job' + k)
        print "In Directory: ", oldDir
        os.chdir(oldDir)
        filelist = os.listdir(oldDir)
        # print "File list:     ", filelist
        for file in filelist:
            # The interim update may contain invalid documents.  Skip
            # over the directory and continue to process the files.
            # -------------------------------------------------------
            if file != 'InvalidDocs':
                f = open(file, 'r')
            else:
                continue
            if file == manifest:
                # Read all lines of the manifest file into a list
                # that will later need to be sorted uniquely
                # -----------------------------------------------
                for line in f:
                    mfFiles.append(line)
                continue
            else:
                # Inspect the file to identify if document is removed or updated
                # --------------------------------------------------------------
                text = f.readline()
            f.close()

            # Create Directory with date stamp
            # --------------------------------
            if not os.path.exists(newDir):
                os.mkdir(newDir)

            # Move the removed files to the remove directory
            # ----------------------------------------------
            if re.search(rmDoc, text):
                # Copy deleted documents to remove directory.
                # Create directory if it doesn't exist
                # -------------------------------------------
                # print 'File' + file + ' got deleted'
                destDir = os.path.join(newDir, 'remove')
   
                if not os.path.exists(destDir):
                    os.mkdir(destDir)
                    rmDir = 1
         
                shutil.copy(file, destDir)
                open(log, "a").write("    %d: Copied %s to %s\n" %
                              (jobId, file, destDir))

            # A single manifest file gets written after all directories 
            # have been read 
            # ---------------------------------------------------------
            # elif file == manifest:
            #     pass
            # Move the updated files to the cdr directory
            # -------------------------------------------
            else:
                # Copy updated documents to update directory.
                # Create directory if it doesn't exist
                # -------------------------------------------
                # print 'File' + file + ' was updated'
                destDir = os.path.join(newDir, 'cdr')
   
                if not os.path.exists(destDir):
                    os.mkdir(destDir)
                    cdrDir = 1
        
                shutil.copy(file, destDir)
                open(log, "a").write("    %d: Copied %s to %s\n" %
                              (jobId, file, destDir))

    # After all directories have been read we need to write a combined
    # manifest file.  Sort and dedup the content before writing
    # ----------------------------------------------------------------
    if len(mfFiles):
        open(log, "a").write("    %d: Writing manifest file\n" %
                        (jobId))
        print "Writing media_catalog.txt file..."

        mfFiles.sort()
        noDups = removeDups(mfFiles)
        os.chdir(newDir)
        f = open(manifest, 'w')
        for line in noDups:
            print >> f, line,
        f.close()

    # We may have created way too many interim update files to be 
    # handled by the FTP mput command. 
    # Create a tar file to be copied the the FTP server instead.
    # -----------------------------------------------------------
    os.chdir(hfDir)
    outFile = os.popen('tar cjf %s %s 2>&1' % (tarName, dateStr))
    output  = outFile.read()
    result  = outFile.close()
    if result:
        sys.stderr.write("tar return code: %d\n" % result)
    if output:
        sys.stderr.write("%s\n" % output)
    sys.stderr.write("%s created\n" % tarName)

    
    # Creating the FTP command file
    # -----------------------------
    open(log, "a").write("    %d: Creating ftp command file\n" %
                        (jobId))
    print "Writing ftp command file..."
    os.chdir(pubDir)
    ftpCmd = open ('FtpInterimDocs.txt', 'w')
    ftpCmd.write('open cipsftp.nci.nih.gov\n')
    ftpCmd.write('cdrdev\n')
    ftpCmd.write('***REMOVED***\n')
    ftpCmd.write('binary\n')
    ftpCmd.write('cd /u/ftp/qa/pdq/incoming/mid-month\n')
    ftpCmd.write('lcd d:/cdr/Output/mid-month\n')
    ftpCmd.write('put ' + tarName + '\n')

    ftpCmd.write('bye\n')
    ftpCmd.close()

    open(log, "a").write("    %d: Copy files to ftp server\n" %
                        (jobId))
    print "Copy files to ftp server..."

    # FTP the Interim documents to ftpserver
    # --------------------------------------
    mycmd = cdr.runCommand("%SYSTEMROOT%/System32/ftp.exe -i -s:FtpInterimDocs.txt")

    open(log, "a").write("    %d: FTP command return code: %s\n" %
                        (jobId, mycmd.code))
    if mycmd.code == 1:
       open(log, "a").write("    %d: ---------------------------\n%s\n" %
                        (jobId, mycmd.output))

    open(log, "a").write("    %d: Ended   at: %s\nJob %d: %s\n" %
                        (jobId, time.ctime(time.time()), jobId, divider))

except SystemExit:
    # We've invoked sys.exit() so we're done.
    pass

except Exception, arg:
    open(log, "a").write("    %d: Failure: %s\nJob %d: %s\n" % 
                        (jobId, arg[0], jobId, divider))

except:
    open(log, "a").write("    %d: Unexpected failure\nJob %d: %s\n" % 
                        (jobId, jobId, divider))
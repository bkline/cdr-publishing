#----------------------------------------------------------------------
#
# $Id: ProtAbstractMailer.py,v 1.23 2007-02-06 22:23:08 bkline Exp $
#
# Master driver script for processing initial protocol abstract mailers.
#
# $Log: not supported by cvs2svn $
# Revision 1.22  2007/02/06 19:07:25  bkline
# Used UnicodeToLatex on protocol ID.
#
# Revision 1.21  2006/10/24 20:29:47  bkline
# Fixed some exception throwing code.
#
# Revision 1.20  2003/06/27 15:11:37  bkline
# Added @@CLOSEMATH@@ placeholder; removed extra backslashes in title
# markup.
#
# Revision 1.19  2003/06/27 14:03:33  bkline
# Plugged in new filter set for protocol abstract mailers.
#
# Revision 1.18  2003/06/24 12:24:11  bkline
# Added code to support inline markup in protocol title.
#
# Revision 1.17  2003/01/22 15:04:25  bkline
# Fixed the fix for Unicode titles in cover letters (converted title
# from utf-8 encoding before applying UnicodeToLatex.convert()).
#
# Revision 1.16  2003/01/22 14:32:55  bkline
# Added calls to UnicodeToLatex.convert() for cover letter.
#
# Revision 1.15  2003/01/15 03:34:52  bkline
# Fixed problem with Unicode in title for cover letter.
#
# Revision 1.14  2002/11/08 21:45:27  bkline
# Added Latin 1 encoding of title.
#
# Revision 1.13  2002/11/08 17:27:06  bkline
# Switch to using professional title for cover letter at Lakshmi's
# request (issue #510).
#
# Revision 1.12  2002/11/07 21:22:07  bkline
# Fix for selection query.
#
# Revision 1.11  2002/10/24 17:52:06  bkline
# Added support for RemailerFor element.
#
# Revision 1.10  2002/10/24 17:17:16  bkline
# Added document version to constructor invocation.
#
# Revision 1.9  2002/10/23 22:04:11  bkline
# Minor adjustments to mailer indexing code.  Switched to using base class
# method for locating mailer include path.  Cosmetic adjustments to cover
# page.
#
# Revision 1.8  2002/10/23 11:44:08  bkline
# Fixed access to base class's __index member.
#
# Revision 1.7  2002/10/22 20:23:29  bkline
# *Really* fixed subset name.
#
# Revision 1.6  2002/10/22 20:22:19  bkline
# Switch to use of makeIndex() from the base class.  Fixed subset name.
#
# Revision 1.5  2002/10/10 17:45:16  bkline
# Mods to cover letters.
#
# Revision 1.4  2002/10/10 13:44:25  bkline
# Ready for testing.
#
# Revision 1.3  2002/10/08 01:43:27  bkline
# Added missing clause to SQL query.  Brought cover letter processing
# closer in line with requirements.  Dropped some unnecessary tweaking of
# the personal address filter output.
#
# Revision 1.2  2002/09/12 23:29:50  ameyer
# Removed common routine from individual mailers to cdrmailer.py.
# Added a few trace statements.
#
# Revision 1.1  2002/01/28 09:36:24  bkline
# Adding remaining CDR scripts.
#
#----------------------------------------------------------------------

import cdr, cdrdb, cdrmailer, re, sys, UnicodeToLatex

#----------------------------------------------------------------------
# Derived class for protocol abstract mailings.
#----------------------------------------------------------------------
class ProtocolAbstractMailer(cdrmailer.MailerJob):

    #------------------------------------------------------------------
    # Overrides method in base class for filling the print queue.
    #------------------------------------------------------------------
    def fillQueue(self):
        self.__getRecipients()
        self.__getDocuments()
        self.__makeIndex()
        self.__makeCoverSheet()
        self.__makeMailers()

    #------------------------------------------------------------------
    # Find lead organization personnel who should receive these mailers.
    #------------------------------------------------------------------
    def __getRecipients(self):
        docType = "InScopeProtocol"
        try:
            self.getCursor().execute("""\
                SELECT DISTINCT recipient.id,
                                recipient.title,
                                protocol.id,
                                protocol.title,
                                pub_proc_doc.doc_version,
                                cdrref.value
                           FROM document recipient
                           JOIN query_term cdrref
                             ON cdrref.int_val = recipient.id
                           JOIN query_term cdrid
                             ON cdrid.doc_id = cdrref.doc_id
                            AND LEFT(cdrid.node_loc, 12) =
                                LEFT(cdrref.node_loc, 12)
                           JOIN query_term idref
                             ON idref.doc_id = cdrid.doc_id
                            AND idref.value = cdrid.value
                           JOIN document protocol
                             ON protocol.id = idref.doc_id
                           JOIN pub_proc_doc
                             ON pub_proc_doc.doc_id = protocol.id
                          WHERE pub_proc_doc.pub_proc = ?
                            AND cdrref.path = '/InScopeProtocol'
                                            + '/ProtocolAdminInfo'
                                            + '/ProtocolLeadOrg'
                                            + '/LeadOrgPersonnel'
                                            + '/Person/@cdr:ref'
                            AND cdrid.path  = '/InScopeProtocol'
                                            + '/ProtocolAdminInfo'
                                            + '/ProtocolLeadOrg'
                                            + '/LeadOrgPersonnel/@cdr:id'
                            AND idref.path  = '/InScopeProtocol'
                                            + '/ProtocolAdminInfo'
                                            + '/ProtocolLeadOrg'
                                            + '/MailAbstractTo'""",
                                            (self.getId(),), 120)
            rows = self.getCursor().fetchall()
            for row in rows:
                recipient = self.getRecipients().get(row[0])
                document  = self.getDocuments().get(row[2])
                if not recipient:
                    self.log("found recipient %s" % row[1])
                    addr = cdrmailer.Address(self.__getRecipAddress(row[5]))
                    recipient = cdrmailer.Recipient(row[0], row[1], addr)
                    self.getRecipients()[row[0]] = recipient
                if not document:
                    document = cdrmailer.Document(row[2], row[3], docType,
                                                  row[4])
                    self.getDocuments()[row[2]] = document
                recipient.getDocs().append(document)
        except cdrdb.Error, info:
            raise Exception("database error finding recipients: %s" %
                            str(info[1][0]))

    #------------------------------------------------------------------
    # Find a protocol lead organization personnel's mailing address.
    #------------------------------------------------------------------
    def __getRecipAddress(self, fragLink):
        try:
            docId, fragId = fragLink.split("#")
        except:
            raise Exception("Invalid fragment link: %s" % fragLink)
        parms = (("fragId", fragId),)
        filters = ["name:Person Address Fragment With Name"]
        rsp = cdr.filterDoc(self.getSession(), filters, docId, parm = parms)
        if type(rsp) == type("") or type(rsp) == type(u""):
            raise Exception("Unable to find address for %s: %s" %
                            (str(fragLink), rsp))
        return rsp[0]

    #------------------------------------------------------------------
    # Produce LaTeX source for all summaries to be mailed out.
    #------------------------------------------------------------------
    def __getDocuments(self):
        filters = [
            "set:Mailer InScopeProtocol Set"
            #"name:Denormalization Filter (1/1): InScope Protocol",
            #"name:Denormalization: sort OrganizationName for Postal Address"
        ]
        for docId in self.getDocuments().keys():
            self.log("generating LaTeX for CDR%010d" % docId)
            doc = self.getDocuments()[docId]
            doc.latex = self.makeLatex(doc, filters, '')
            doc.profTitle = self.__getProfTitle(doc)

    #------------------------------------------------------------------
    # Get the text content of the /InScopeProtocol/ProtocolTitle where
    # the Type attribute = 'Professional'.
    #------------------------------------------------------------------
    def __getProfTitle(self, doc):
        id      = doc.getId() #"CDR%010d" % doc.getId()
        ver     = doc.getVersion()
        filters = ['name:Get Protocol Professional Title']
        result  = cdr.filterDoc('guest', filters, id, docVer = ver,
                                parm = [('useLatexMarkup', 'Y')])
        if type(result) in (type(""), type(u"")):
            raise Exception("failure filtering document %s: %s" %
                            (docId, result))
        if result[0]:
            title = UnicodeToLatex.convert(unicode(result[0], "utf-8"))
            return (title.replace("@@EMPH@@",      r"\emph{")
                         .replace("@@BOLD@@",      r"\textbf{")
                         .replace("@@SUPER@@",     r"$^{")
                         .replace("@@SUB@@",       r"$_{")
                         .replace("@@CLOSEBR@@",   r"}")
                         .replace("@@CLOSEMATH@@", r"}$"))
        return "[No Protocol Professional Title found]"

    #------------------------------------------------------------------
    # Generate an index of the mailers order by country/postal code.
    #------------------------------------------------------------------
    def __makeIndex(self):
    
        # Hand off the work to the base class.
        self.makeIndex()

    #------------------------------------------------------------------
    # Generate a main cover page and add it to the print queue.
    #------------------------------------------------------------------
    def __makeCoverSheet(self):
        filename = "MainCoverPage.txt"
        f = open(filename, "w")
        f.write("\n\n%s\n\n" % self.getSubset())
        f.write("Job Number: %d\n\n" % self.getId())
        for country, zip, recip, doc in self.getIndex():
            title = doc.getTitle().encode('latin-1', 'replace')
            if len(title) > 60: title = "%s ..." % title[:60]
            f.write("  Recipient: %d\n" % recip.getId())
            f.write("       Name: %s\n" % recip.getName())
            f.write("    Country: %s\n" % country)
            f.write("Postal Code: %s\n" % zip)
            f.write("   Protocol: %d\n" % doc.getId())
            f.write("      Title: %s\n\n" % title)
        f.write("\f")
        f.close()
        job = cdrmailer.PrintJob(filename, cdrmailer.PrintJob.PLAIN)
        self.addToQueue(job)

    #------------------------------------------------------------------
    # Walk through the index, generating protocol mailers.
    #------------------------------------------------------------------
    def __makeMailers(self):
        coverLetterParm     = self.getParm("CoverLetter")
        basePath            = self.getMailerIncludePath() + "/"
        coverLetterName     = basePath + coverLetterParm[0]
        coverLetterFile     = open(coverLetterName)
        coverLetterTemplate = coverLetterFile.read()
        coverLetterFile.close()
        for elem in self.getIndex():
            recip, doc = elem[2:]
            self.__makeMailer(recip, doc, coverLetterTemplate)

    #------------------------------------------------------------------
    # Create a protocol abstract mailer.
    #------------------------------------------------------------------
    def __makeMailer(self, recip, doc, template):

        # Add document to the repository for tracking replies to the mailer.
        remailerFor = None
        docId       = doc.getId()
        if self.getSubset() == 'Protocol-Annual abstract remail':
            try:
                self.getCursor().execute("""\
                    SELECT MAX(prot_mailer.doc_id)
                      FROM query_term prot_mailer
                      JOIN query_term mailer_type
                        ON prot_mailer.doc_id = mailer_type.doc_id
                     WHERE prot_mailer.path = '/Mailer/Document/@cdr:ref'
                       AND mailer_type.path = '/Mailer/Type'
                       AND mailer_type.value = 'Protocol-Annual abstract'
                       AND prot_mailer.int_val = %d""" % docId)
                row = self.getCursor().fetchone()
                if not row:
                    raise Exception("Lookup for original mailer failed for "
                                    "protocol %d" % docId)
                remailerFor = row[0]
            except cdrdb.Error, info:
                raise Exception("database error finding original mailer: %s" %
                                str(info[1][0]))
        mailerId = self.addMailerTrackingDoc(doc, recip, self.getSubset(),
                                             remailerFor)

        # Create a mailing label.
        latex     = self.createAddressLabelPage(recip.getAddress())
        basename  = 'MailingLabel-%d-%d' % (recip.getId(), doc.getId())
        jobType   = cdrmailer.PrintJob.COVERPAGE
        self.addToQueue(self.makePS(latex, 1, basename, jobType))

        # Create the cover letter.
        address   = self.formatAddress(recip.getAddress())
        docTitle  = doc.getTitle()
        pieces    = docTitle.split(';', 1)
        if len(pieces) != 2:
            raise Exception("Protocol title for CDR%d missing component: %s" %
                            (doc.getId(), docTitle))
        protId    = UnicodeToLatex.convert(pieces[0])
        protTitle = doc.profTitle #pieces[1]
        docId     = "%d (Tracking ID: %d)" % (doc.getId(), mailerId)

        # Replace placeholders:
        latex     = template.replace('@@ADDRESS@@', address)
        latex     = latex.replace('@@PROTOCOLID@@', protId)
        latex     = latex.replace('@@PROTOCOLTITLE@@', protTitle)

        basename  = 'CoverLetter-%d-%d' % (recip.getId(), doc.getId())
        jobType   = cdrmailer.PrintJob.COVERPAGE
        self.addToQueue(self.makePS(latex, 1, basename, jobType))

        # Customize the LaTeX for this copy of the protocol.
        nPasses   = doc.latex.getLatexPassCount()
        latex     = doc.latex.getLatex()
        latex     = latex.replace('@@DOCID@@', str(doc.getId()))
        latex     = latex.replace('@@MailerDocID@@', str(mailerId))
        basename  = 'Mailer-%d-%d' % (recip.getId(), doc.getId())
        jobType   = cdrmailer.PrintJob.MAINDOC
        self.addToQueue(self.makePS(latex, nPasses, basename, jobType))

if __name__ == "__main__":
    sys.exit(ProtocolAbstractMailer(int(sys.argv[1])).run())
#include <sal/config.h>  	// System abstraction layers
#include <sal/main.h>
#include <rtl/ustring.hxx> 	// Platform independent strings
#include <rtl/bootstrap.hxx>
#include <osl/file.hxx>		// Platform specific things	
#include <osl/process.h>

#include <cppuhelper/bootstrap.hxx>	// Universal Network Objects (UNO) API Components
#include <comphelper/processfactory.hxx>
#include <com/sun/star/lang/XMultiServiceFactory.hpp>
#include <com/sun/star/uno/XComponentContext.hpp>

#include <vcl/svapp.hxx>	// Application definitions
#include <tools/extendapplicationenvironment.hxx> 	// Extension helpers

#include <scdll.hxx>	// LibreCalc specific headers
#include <docsh.hxx>
#include <document.hxx>
#include <address.hxx>
#include <formula/grammar.hxx>
#include <formula/errorcodes.hxx>

using namespace ::com::sun::star::uno;
using namespace ::com::sun::star::lang;
using namespace cppu;

OUString getExecutableDir()
{
	OUString uri;
	if (osl_getExecutableFile(&uri.pData) != osl_Process_E_None) {
	    abort();
	}
	sal_Int32 lastDirSeparatorPos = uri.lastIndexOf('/');
	if (lastDirSeparatorPos >= 0) {
	    uri = uri.copy(0, lastDirSeparatorPos + 1);
	}
	return uri;
}

SAL_IMPLEMENT_MAIN()
{
	// Set environment for headless
	setenv("SAL_USE_VCLPLUGIN", "svp", 1);
	setenv("SAL_DISABLE_PRINTERLIST", "1", 1);
	setenv("SAL_DISABLE_DEFAULTPRINTER", "1", 1);
	setenv("SAL_NO_FONT_LOOKUP", "1", 1);
	setenv("SC_NO_THREADED_CALCULATION", "1", 1);

	// Commandline args
	int argc = 1;
	char prog[] = "harn3";
	char* argv[] = {prog, nullptr};
	osl_setCommandArgs(argc, argv);

	// Bootstrap directories
	OUString sExecDir = getExecutableDir();
	rtl::Bootstrap::set(u"BRAND_BASE_DIR"_ustr, sExecDir);

	// Extend application env
	tools::extendApplicationEnvironment();

	// Bootstrap UNO component context
	Reference<XComponentContext> xContext;
	try{
		xContext = defaultBootstrap_InitialComponentContext();
	} catch (const Exception& e) {
		fprintf(stderr, "ERROR: Failed to bootstrap UNO: %s\n", 
				OUStringToOString(e.Message, RTL_TEXTENCODING_UTF8).getStr());
		return 1;
	}

	// Get service manager and register it
	Reference<XMultiServiceFactory> xServiceManager(
			xContext->getServiceManager(), UNO_QUERY);
	if (!xServiceManager.is()) {
		fprintf(stderr, "ERROR: Failed to get service manager\n");
		return 1;
	}
	comphelper::setProcessServiceFactory(xServiceManager);

	// Enable Headless
	Application::EnableHeadlessMode(false);

	// Initialize VCL
	if( !InitVCL() ) {
		fprintf(stderr, "ERROR: VCL init failed\n");
		return 1;
	}

	// Init LibreOffice Calc Module
	ScDLL::Init();

	// Create document shell to manage lifecycle
	ScDocShellRef xDocShell = new ScDocShell(
		SfxModelFlags::EMBEDDED_OBJECT |
		SfxModelFlags::DISABLE_EMBEDDED_SCRIPTS |
		SfxModelFlags::DISABLE_DOCUMENT_RECOVERY
	);

	// Initialize for headless | or possible xDocShell->DoInitNew() for normal operations 
	xDocShell->DoInitUnitTest();

	// Get direct reference to document
	ScDocument& rDoc = xDocShell->GetDocument();

	// Create a sheet
	rDoc.InsertTab(0, u"Sheet1"_ustr);

	// Set Values example
	// ScAddress(Col, Row, Sheet)
	rDoc.SetValue(ScAddress(0, 0, 0), 1);	// A1 = 1
	rDoc.SetValue(ScAddress(0, 1, 0), 2); 	// A2 = 2
	rDoc.SetValue(ScAddress(0, 2, 0), 3); 	// A3 = 3
	
	// Set Formulas Example
	rDoc.SetFormula(
		ScAddress(1, 0, 0),			// B1
		u"=SUM(A1:A3)"_ustr,			// SUM ABOVE should equal 6
		formula::FormulaGrammar::GRAM_ENGLISH	// EXPLICIT ENGLISH LANG
	);

	// Calc all formulas
	rDoc.CalcAll();

	// Check results
	double val = rDoc.GetValue(ScAddress(1, 0, 0));
	printf("Result: %.2f\n", val); // is it 6?
				     
	// Clean up
	xDocShell->DoClose();
	xDocShell.clear();

	return 0;
}

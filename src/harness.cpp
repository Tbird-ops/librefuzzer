#include <sal/config.h>  	// System abstraction layers
#include <sal/main.h>
#include <rtl/ustring.hxx> 	// Platform independent strings
#include <rtl/bootstrap.hxx>
#include <osl/file.hxx>		// Platform specific things	
#include <osl/process.h>

#include <helper/qahelper.hxx>

#include <cppuhelper/bootstrap.hxx>	// Universal Network Objects (UNO) API Components
#include <comphelper/processfactory.hxx>
#include <com/sun/star/lang/XMultiServiceFactory.hpp>
#include <com/sun/star/uno/XComponentContext.hpp>

#include <scdll.hxx>	// LibreCalc specific headers
#include <docsh.hxx>
#include <document.hxx>
#include <address.hxx>
#include <formula/grammar.hxx>
#include <formula/errorcodes.hxx>

using namespace ::com::sun::star::uno;
using namespace ::com::sun::star::lang;
using namespace cppu;


//SAL_IMPLEMENT_MAIN()
int main(int argc, char** argv)
{
	// Run common initialization things
	ScUcalcTestBase::setUp();

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

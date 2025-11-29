LO_SRC=/home/tbird/source/librefuzz/office_files/libreoffice-25.8.1.1

INCLUDES=-I$(LO_SRC)/config_host -I$(LO_SRC)/include -I$(LO_SRC)/sc/inc -I$(LO_SRC)/sc/source/ui/inc -I$(LO_SRC)/workdir/UnoApiHeadersTarget/offapi/normal -I$(LO_SRC)/workdir/UnoApiHeadersTarget/udkapi/normal -I$(LO_SRC)/vcl/inc -I$(LO_SRC)/workdir/UnpackedTarball/harfbuzz/src/ -I/usr/include/cairo -I$(LO_SRC)/workdir/UnpackedTarball/pdfium/third_party/freetype/src/include -I$(LO_SRC)/workdir/UnpackedTarball/cppunit/include -I$(LO_SRC)/sc/qa/unit

LIBPATHS=-L$(LO_SRC)/instdir/program -L$(LO_SRC)/instdir/sdk/lib

LIBS=-luno_sal -luno_salhelpergcc3 -luno_cppu -luno_cppuhelpergcc3 -lcomphelper -ltllo -lsvllo -lsvxcorelo -lsfxlo -lvcllo -lsclo

RPATH=-Wl,-rpath,$(LO_SRC)/instdir/program:$(LO_SRC)/instdir/sdk/lib

harness: harness.cpp
	g++ -std=c++23 -fPIC -g -DSAL_UNX -DUNX -DLINUX $(INCLUDES) harness.cpp $(LIBPATHS) $(LIBS) $(RPATH) -o harness

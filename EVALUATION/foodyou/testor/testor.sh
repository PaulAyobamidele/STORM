# TESTOR_DIR is defined and EXPORTED after the CADP check below, so that
# coverage.svl -- which builds its testor path from $TESTOR_DIR -- inherits it.

# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------
if [ "$1" = -clean ] ; then
	rm -f *ctg*.bcg *tc*.bcg *.log
	[ -f coverage.log ] && svl -clean coverage.svl
	rm -f composed_foodyou_copy.bcg tp_happy.bcg
	rm -f bisimulator generator reductor testor tgv
	rm -f *.o *.t *.f *.lotos *.lib *.h
	exit
fi

# ---------------------------------------------------------------------------
# environment checks
# ---------------------------------------------------------------------------
if [ "$CADP" = "" ] ; then
	echo "$0: \$CADP should point to the installation directory of CADP"
	exit 1
elif [ ! -d "$CADP" ] ; then
	echo "$0: directory \$CADP does not exist"
	exit 1
fi

ARCH=`$CADP/com/arch`

# coverage.svl locates testor via $TESTOR_DIR; default it to the CADP tree
# (so $TESTOR_DIR/bin.$ARCH/testor.a resolves) and EXPORT so svl inherits it.
export TESTOR_DIR=${TESTOR_DIR:-$CADP}

# resolve the testor plugin: a local ./testor (as used for spliit), else the
# one under TESTOR_DIR (demo template), else the one shipped with CADP
if [ -r ./testor ] ; then
	TESTOR=./testor
elif [ -r "$TESTOR_DIR/bin.$ARCH/testor.a" ] ; then
	TESTOR=$TESTOR_DIR/bin.$ARCH/testor.a
else
	TESTOR=$CADP/bin.$ARCH/testor.a
fi
if [ ! -r "$TESTOR" ] ; then
	echo "$0: cannot find testor ('./testor', '$TESTOR_DIR/bin.$ARCH/testor.a', or '$CADP/bin.$ARCH/testor.a')"
	exit 1
fi
echo "using testor: $TESTOR"

# limit the available virtual memory to 80% of the physical RAM
MEMORY_SIZE=`$CADP/bin.$ARCH/cadp_memory -physical`
MEMORY_LIMIT=`echo "0.8 * $MEMORY_SIZE / 1024" | bc -l | sed 's/[.][0-9]*$//'`
ulimit -v $MEMORY_LIMIT
echo "limiting virtual memory to $MEMORY_LIMIT kbytes"

echo "-------------------------------------------------------------------------"
echo "FoodYou -- COMPOSED (SPEC || SI) against test purpose tp_happy"
echo "-------------------------------------------------------------------------"

# ---------------------------------------------------------------------------
# 1. test purpose -> BCG  (TP_ACCEPT->ACCEPT, TP_REFUSE->REFUSE)
# ---------------------------------------------------------------------------
echo
echo "==> 1. building test purpose (tp_happy.bcg)"
lnt.open -main MAIN -silent tp_happy.lnt generator \
	-rename accept.ren -rename refuse.ren tp_happy.bcg

# ---------------------------------------------------------------------------
# 2. test case on the fly, using testor
# ---------------------------------------------------------------------------
echo
echo "==> 2. extracting test case on the fly (foodyou.tc.bcg)"
lnt.open -main COMPOSED compose_foodyou_copy.lnt $TESTOR \
	-io foodyou.io tp_happy.bcg foodyou.tc.bcg

# ---------------------------------------------------------------------------
# 3. complete test graph, using testor (-all)
# ---------------------------------------------------------------------------
echo
echo "==> 3. computing complete test graph (foodyou.ctg.bcg)"
lnt.open -main COMPOSED compose_foodyou_copy.lnt $TESTOR \
	-io foodyou.io -all tp_happy.bcg foodyou.ctg.bcg

# sanity: the extracted test case must be included in the complete test graph
echo
echo "==> checking the test case is included in the complete test graph"
bcg_open foodyou.ctg.bcg bisimulator -greater foodyou.tc.bcg 2>&1 |
	grep -v '^bcg_open:' | sed '/^$/d'

# ---------------------------------------------------------------------------
# 4. coverage: complete the test plan to cover the model
# ---------------------------------------------------------------------------
echo
echo "==> 4. coverage"
# explicit LTS of the composed model (input to the coverage SVL script)
if [ ! -r composed_foodyou_copy.bcg ] ; then
	lnt.open -main COMPOSED compose_foodyou_copy.lnt generator composed_foodyou_copy.bcg
fi
# pull coverage.svl from the CADP demo directory if it is not local
if [ ! -r coverage.svl ] && [ -r "$CADP/demo/coverage.svl" ] ; then
	cp "$CADP/demo/coverage.svl" .
fi
if [ -r coverage.svl ] ; then
	svl coverage.svl composed_foodyou_copy.bcg foodyou.io tp_happy.bcg
else
	echo "    (skipped: coverage.svl not found here nor at \$CADP/demo/coverage.svl)"
fi

# ---------------------------------------------------------------------------
# tidy up intermediate compiler artefacts
# ---------------------------------------------------------------------------
rm -f *.o *.t *.f *.lotos *.lib *.h

echo
echo "done. Artefacts: foodyou.tc.bcg (test case), foodyou.ctg.bcg (complete test graph)"

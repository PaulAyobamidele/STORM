#!/bin/sh
# testor_all.sh — like testor.sh, but loops over EVERY test purpose and records
# per-test-purpose coverage of the COMPOSED model via CADP's coverage.svl.
# Run in the flat testor dir on the CADP node (narval):
#   export CADP=/home/paulad/cadp; export PATH=$CADP/com:$CADP/bin.x64:$PATH
#   cd /scratch/paulad/testor_foodyou
#   sh testor_all.sh            # coverage only (fast)
#   DO_CTG=1 sh testor_all.sh   # also build the complete test graph + tc<=ctg sanity (slow)

TPS="happy ue1_kill input_invalid extapi_fail cache_stale disruption_db db_corrupt storage_full storage_media"

# ---------------------------------------------------------------- cleanup
if [ "$1" = -clean ] ; then
        rm -f *ctg*.bcg *tc*.bcg tp_*.bcg coverage_*.log *.log
        [ -f coverage.log ] && svl -clean coverage.svl
        rm -f composed_foodyou_copy.bcg
        rm -f bisimulator generator reductor testor tgv
        rm -f *.o *.t *.f *.lotos *.lib *.h
        exit
fi

# ---------------------------------------------------------------- env checks
if [ "$CADP" = "" ] ; then echo "$0: \$CADP must point to the CADP install"; exit 1
elif [ ! -d "$CADP" ] ; then echo "$0: \$CADP does not exist"; exit 1 ; fi
ARCH=`$CADP/com/arch`
export TESTOR_DIR=${TESTOR_DIR:-$CADP}
if   [ -r ./testor ] ; then TESTOR=./testor
elif [ -r "$TESTOR_DIR/bin.$ARCH/testor.a" ] ; then TESTOR=$TESTOR_DIR/bin.$ARCH/testor.a
else TESTOR=$CADP/bin.$ARCH/testor.a ; fi
[ -r "$TESTOR" ] || { echo "$0: cannot find testor"; exit 1; }
echo "using testor: $TESTOR"

# limit virtual memory to 80% of physical RAM (as in testor.sh)
MEMORY_SIZE=`$CADP/bin.$ARCH/cadp_memory -physical`
MEMORY_LIMIT=`echo "0.8 * $MEMORY_SIZE / 1024" | bc -l | sed 's/[.][0-9]*$//'`
ulimit -v $MEMORY_LIMIT
echo "limiting virtual memory to $MEMORY_LIMIT kbytes"

# ---------------------------------------------------------------- baseline (ONCE)
# explicit LTS of the composed model = the coverage baseline, reused by every tp.
if [ ! -r composed_foodyou_copy.bcg ] ; then
        echo "==> building COMPOSED model LTS (composed_foodyou_copy.bcg)"
        lnt.open -main COMPOSED compose_foodyou_copy.lnt generator composed_foodyou_copy.bcg
fi
# pull coverage.svl from the CADP demo dir if it is not local
if [ ! -r coverage.svl ] && [ -r "$CADP/demo/coverage.svl" ] ; then
        cp "$CADP/demo/coverage.svl" .
fi
[ -r coverage.svl ] || echo "WARNING: coverage.svl not found (here or \$CADP/demo) — coverage step will be skipped"

# ---------------------------------------------------------------- per test purpose
for TP in $TPS ; do
        [ -r "tp_${TP}.lnt" ] || { echo "== $TP: tp_${TP}.lnt missing, skip"; continue; }
        echo "======================================================================"
        echo "== TEST PURPOSE: $TP"
        echo "======================================================================"

        # 1. test purpose -> BCG
        lnt.open -main MAIN -silent tp_${TP}.lnt generator \
                -rename accept.ren -rename refuse.ren tp_${TP}.bcg

        # 2. test case on the fly (kept per-tp)
        lnt.open -main COMPOSED compose_foodyou_copy.lnt $TESTOR \
                -io foodyou.io tp_${TP}.bcg foodyou_${TP}.tc.bcg

        # 3. (optional, slow) complete test graph + sanity: tc <= ctg
        if [ "${DO_CTG:-0}" = 1 ] ; then
                lnt.open -main COMPOSED compose_foodyou_copy.lnt $TESTOR \
                        -io foodyou.io -all tp_${TP}.bcg foodyou_${TP}.ctg.bcg
                echo "   tc <= ctg :"
                bcg_open foodyou_${TP}.ctg.bcg bisimulator -greater foodyou_${TP}.tc.bcg 2>&1 \
                        | grep -v '^bcg_open:' | sed '/^$/d'
        fi

        # 4. coverage of THIS test purpose over the composed model
        if [ -r coverage.svl ] ; then
                echo "   coverage (-> coverage_${TP}.log):"
                svl coverage.svl composed_foodyou_copy.bcg foodyou.io tp_${TP}.bcg 2>&1 \
                        | tee coverage_${TP}.log
                # keep coverage.svl's own artefact per-tp if it writes a fixed name
                [ -r coverage.bcg ] && mv -f coverage.bcg coverage_${TP}.bcg
        fi
done

rm -f *.o *.t *.f *.lotos *.lib *.h
echo
echo "done. per-tp coverage: coverage_<tp>.log ; test cases: foodyou_<tp>.tc.bcg"

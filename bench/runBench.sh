#!/bin/bash

#set -x
sleep 13000
h2oBuild=
benchmarks="benchmarks"
DATE=`date +%Y-%m-%d`
archive="Archive"

function all {
    doAlgo pca;   wait;  makeDead > /dev/null;
    doAlgo kmeans wait;  makeDead > /dev/null;
    doAlgo glm;   wait;  makeDead > /dev/null;
    doAlgo glm2;  wait;  makeDead > /dev/null;
    doAlgo gbm;   wait;  makeDead > /dev/null;
#    doAlgo gbmgrid
#    doAlgo bigkmeans
}

function doAlgo {
    echo "Clear caches!"
    bash startloggers.sh ${JSON} clear_ 

    echo "Running $1 benchmark..."
    echo "Changing little logger phase..."
    bash startloggers.sh ${JSON} changePhase $1

    pyScript="BMscripts/"$1"Bench.py"
    wait
    if [ ! $1 = "bigkmeans" ]
    then
        python ${pyScript} -cj BMscripts/${JSON} ${h2oBuild} False Air1x;    wait; makeDead > /dev/null;
        zip -r ${archive}/${h2oBuild}-${DATE}-$1-Air1x;                      wait; rm -rf sandbox/;
        python ${pyScript} -cj BMscripts/${JSON} ${h2oBuild} False Air10x;   wait; makeDead > /dev/null;
        zip -r ${archive}/${h2oBuild}-${DATE}-$1-Air10x;                     wait; rm -rf sandbox/;
        python ${pyScript} -cj BMscripts/${JSON} ${h2oBuild} False AllB1x;   wait; makeDead > /dev/null;
        zip -r ${archive}/${h2oBuild}-${DATE}-$1-AllB1x;                     wait; rm -rf sandbox/;
        python ${pyScript} -cj BMscripts/${JSON} ${h2oBuild} False AllB10x;  wait; makeDead > /dev/null;
        zip -r ${archive}/${h2oBuild}-${DATE}-$1-AllB10x;                    wait; rm -rf sandbox/;
        python ${pyScript} -cj BMscripts/${JSON} ${h2oBuild} False AllB100x; wait; makeDead > /dev/null;
        zip -r ${archive}/${h2oBuild}-${DATE}-$1-AllB100x;                   wait; rm -rf sandbox/;
        python ${pyScript} -cj BMscripts/${JSON} ${h2oBuild} False Air100x;  wait; makeDead > /dev/null;
        zip -r ${archive}/${h2oBuild}-${DATE}-$1-Air100x;                    wait; rm -rf sandbox/;
    else
        python ${pyScript} ${h2oBuild} ${DEBUG} #bigKM can also run in debug
        wait
    fi
    bash startloggers.sh ${JSON} ice $1 #gather up the ice h2ologs from the machines for this phase
}

function makeDead {
    ps -efww | grep h2o|grep spencer|grep jar| awk '{print $2}' | xargs kill
    ps -efww | grep h2o|grep 0xdiag |grep jar| awk '{print $2}' | xargs kill
}

function debug {
    for a in $@
    do
        python BMscripts/$a"Bench.py" -cj BMscripts/${JSON} ${h2oBuild} True Air1x;    wait; 
        python BMscripts/$a"Bench.py" -cj BMscripts/${JSON} ${h2oBuild} True Air10x;   wait; 
        python BMscripts/$a"Bench.py" -cj BMscripts/${JSON} ${h2oBuild} True AllB1x;   wait; 
        python BMscripts/$a"Bench.py" -cj BMscripts/${JSON} ${h2oBuild} True AllB10x;  wait; 
        python BMscripts/$a"Bench.py" -cj BMscripts/${JSON} ${h2oBuild} True AllB100x; wait; 
        python BMscripts/$a"Bench.py" -cj BMscripts/${JSON} ${h2oBuild} True Air100x;  wait; 
        #python BMscripts/$a"Bench.py" -cj BMscripts/${JSON} ${h2oBuild} ${DEBUG}
    done
}


usage()
{
cat << EOF

USAGE: $0 [options]

This script obtains the latest h2o jar from S3 and runs the benchmarks for PCA, KMeans, GLM, and BigKMeans.

OPTIONS:
   -h      Show this message
   -t      Run task:
               Choices are:
                   all        -- Runs PCA, GLM, KMEANS, GBM, GLM2, GBMGRID, and BIGKMEANS
                   pca        -- Runs PCA on Airlines/AllBedrooms/Covtype data
                   kmeans     -- Runs KMeans on Airlines/AllBedrooms/Covtype data
                   glm        -- Runs logistic regression on Airlines/AllBedrooms/Covtype data
                   glm2       -- Runs logistic regression on Airlines/AllBedrooms/Covtype data
                   gbm        -- Runs GBM on Airlines/AllBedrooms/Covtype data
                   gbmgrid    -- Runs GBM grid search on Airlines/AllBedrooms/Covtype data
                   bigkmeans  -- Runs KMeans on 180 GB & 1TB of synthetic data
                   
   -j      JSON config:
               Choices are:
                   161        -- Runs benchmark(s) on single machine on 161 (100GB)
                   162        -- Runs benchmark(s) on single machine on 162 (100GB)
                   163        -- Runs benchmark(s) on single machine on 163 (100GB)
                   164        -- Runs benchmark(s) on single machine on 164 (100GB)
         		   161_163    -- Runs benchmark(s) on four machines 161-163 (133GB Each)
                   161_164    -- Runs benchmark(s) on four machines 161-164 (100GB Each)
EOF
}

TASK=
JSON=
BUILDN=
DEBUG=0
LOG=0
while getopts "ht:j:b:dL" OPTION
do
  case $OPTION in
    h)
      usage
      exit 1
      ;;
    t)
      TEST=$OPTARG
      ;;
    j)
      JSON=$OPTARG
      ;;
    b)
      BUILDN=$OPTARG
      ;;
    d)
      DEBUG=1
      LOG=0
      ;;
    L)
      LOG=1
      ;;
    ?)
      usage
      exit 1
      ;;
    *)
      usage
      exit 1
      ;;
  esac
done

if [ -z "$TEST" ] || [ -z "$JSON" ]
then
    usage
    exit
fi

bash S3getLatest.sh
wait
dir=`pwd`
latest=$dir/latest
if [ ! -f $latest ]
then
    echo "No 'latest' file was found..."
    echo "Either create one, or use S3getLatest.sh."
    exit 1
fi
h2oBuild=`cat latest`

if [ ! -d ${benchmarks}/${h2oBuild}/${DATE} ]; then
  mkdir -p ${benchmarks}/${h2oBuild}/${DATE}
fi

if [ ${LOG} -eq 1 ]
then
    #global starttime out to all loggers
    starttime=`date +%s`
    echo $starttime > BMLogs/starttime

    #Gentlemen...Start your loggers!
    bash startloggers.sh ${JSON} big
    bash startloggers.sh ${JSON} little
fi

if [ ${DEBUG} -eq 1 ]
then
    echo "Running in debug mode... "
    if [ ${TEST} = "all" ] 
    then
        debug pca glm kmeans glm2 gbm #gbmgrid bigkmeans
        wait
    else
        debug ${TEST}
        wait
    fi
    wait
else
    if [ ! ${TEST} = "all" ]
        then
            doAlgo ${TEST}
        else
            ${TEST}
        fi
        wait
fi

bash startloggers.sh ${JSON} stop_

#remove annoying useless files
rm pytest*flatfile*

#archive nohup
if [ -a nohup.out ]; then
    mv nohup.out ${archive}/${h2oBuild}-${DATE}-nohup.out
fi

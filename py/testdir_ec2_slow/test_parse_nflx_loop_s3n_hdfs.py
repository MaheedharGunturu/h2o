import unittest, sys, random, time
sys.path.extend(['.','..','py'])
import h2o, h2o_cmd, h2o_browse as h2b, h2o_import as h2i, h2o_hosts, h2o_glm
import h2o_jobs
import logging

class Basic(unittest.TestCase):
    def tearDown(self):
        ### print "FAILED: waiting for you to terminate after looking at things"
        ### time.sleep(360000)
        h2o.check_sandbox_for_errors()

    @classmethod
    def setUpClass(cls):
        print "Will build clouds with incrementing heap sizes and import folder/parse"

    @classmethod
    def tearDownClass(cls):
        # the node state is gone when we tear down the cloud, so pass the ignore here also.
        h2o.tear_down_cloud(sandbox_ignore_errors=True)

    def test_parse_nflx_loop_s3n_hdfs(self):
        DO_GLM = False
        DO_GLMGRID = False
        USE_HOME2 = False
        USE_S3 = False
        noPoll = False
        benchmarkLogging = ['jstack','iostats']
        benchmarkLogging = ['iostats']
        benchmarkLogging = []
        # typical size of the michal files
        avgMichalSize = 116561140
        avgSynSize = 4020000
        synSize = 183

        if USE_HOME2:
            csvFilenameList = [
                # this should hit the "more" files too?
                (["10k_small_gz"], "00[0-4][0-9]_syn.csv.gz", "file_50.dat.gz", 50 * synSize , 700),
                (["10k_small_gz"], "[0][1][0-9][0-9]_.*", "file_100.dat.gz", 100 * synSize , 700),
                (["10k_small_gz"], "[0][0-4][0-9][0-9]_.*", "file_500.dat.gz", 500 * synSize , 700),
                (["10k_small_gz"], "[0][0-9][0-9][0-9]_.*", "file_1000.dat.gz", 1000 * synSize , 700),
                # (["10k_small_gz"], "[0-4][0-9][0-9][0-9]_.*", "file_5000.dat.gz", 5000 * synSize , 700),
                # (["10k_small_gz"], "[0-9][0-9][0-9][0-9]_.*", "file_10000.dat.gz", 10000 * synSize , 700),
            ]
        else:
            csvFilenameList = [
                (["manyfiles-nflx-gz"], "file_1[0-9][0-9].dat.gz", "file_100_A.dat.gz", 100 * avgMichalSize, 3600),
                (["manyfiles-nflx-gz"], "file_[1-2][0-5][0-9].dat.gz", "file_120_A.dat.gz", 120 * avgMichalSize, 3600),
                (["manyfiles-nflx-gz"], "file_[1-2][0-6][0-9].dat.gz", "file_140_A.dat.gz", 140 * avgMichalSize, 3600),
                (["manyfiles-nflx-gz"], "file_[1-2][0-7][0-9].dat.gz", "file_160_A.dat.gz", 160 * avgMichalSize, 3600),
                (["manyfiles-nflx-gz"], "file_[1-2][0-8][0-9].dat.gz", "file_180_A.dat.gz", 180 * avgMichalSize, 3600),
                (["manyfiles-nflx-gz"], "file_[12][0-9][0-9].dat.gz", "file_200_A.dat.gz", 200 * avgMichalSize, 3600),
                (["manyfiles-nflx-gz"], "file_[123][0-9][0-9].dat.gz", "file_300_A.dat.gz", 300 * avgMichalSize, 3600),
                (["manyfiles-nflx-gz"], "file_[123][0-9][0-9].dat.gz", "file_300_B.dat.gz", 300 * avgMichalSize, 3600),
                (["manyfiles-nflx-gz"], "file_[123][0-9][0-9].dat.gz", "file_300_C.dat.gz", 300 * avgMichalSize, 3600),
                (["manyfiles-nflx-gz"], "file_1.dat.gz", "file_1.dat.gz", 1 * avgMichalSize, 300),
                (["manyfiles-nflx-gz"], "file_[2][0-9].dat.gz", "file_10.dat.gz", 10 * avgMichalSize, 700),
                (["manyfiles-nflx-gz"], "file_[34][0-9].dat.gz", "file_20.dat.gz", 20 * avgMichalSize, 900),
                (["manyfiles-nflx-gz"], "file_[5-9][0-9].dat.gz", "file_50_A.dat.gz", 50 * avgMichalSize, 3600),
                (["manyfiles-nflx-gz"], "file_1[0-4][0-9].dat.gz", "file_50_B.dat.gz", 50 * avgMichalSize, 3600),
                (["manyfiles-nflx-gz"], "file_1[0-9][0-9].dat.gz", "file_100_A.dat.gz", 100 * avgMichalSize, 3600),
                (["manyfiles-nflx-gz"], "file_2[0-9][0-9].dat.gz", "file_100_B.dat.gz", 100 * avgMichalSize, 3600),
            ]

            # import doesn't do pattern match.
            csvFilenameList = [
                # beware: the files should be non-overlapping sequentially if noPoll is used, to avoid deleting keys in use    
                (["A-800-manyfiles-nflx-gz"],
                    "*file_[0-9]*.dat.gz", "file_A_200_x55.dat.gz", 200 * (avgMichalSize/2), 7200),
                (["A-800-manyfiles-nflx-gz", "B-800-manyfiles-nflx-gz"],
                    "*file_[0-9]*.dat.gz", "file_A_400_x55.dat.gz", 400 * (avgMichalSize/2), 7200),
                (["A-800-manyfiles-nflx-gz", "B-800-manyfiles-nflx-gz", "C-800-manyfiles-nflx-gz", "D-800-manyfiles-nflx-gz"],
                    "*file_[0-9]*.dat.gz", "file_A_800_x55.dat.gz", 800 * (avgMichalSize/2), 7200),
            ]

        print "Using the -.gz files from s3"
        # want just s3n://home-0xdiag-datasets/manyfiles-nflx-gz/file_1.dat.gz

        # split out the pattern match and the filename used for the hex
        trialMax = 1
        pollTimeoutSecs = 180
        retryDelaySecs = 10
        # use i to forward reference in the list, so we can do multiple outstanding parses below
        for i, (csvFolderList, csvFilepattern, csvFilename, totalBytes, timeoutSecs) in enumerate(csvFilenameList):

            if USE_HOME2:
                bucket = "home2-0xdiag-datasets"
            else:
                bucket = "home-0xdiag-datasets"

            ## for tryHeap in [54, 28]:
            h2oPerNode = 1
            # h1.4xlarge 60.5GB dram
            for tryHeap in [28]:
                if USE_S3:
                    protocol = "s3"
                else:
                    protocol = "s3n"
                print "\n", tryHeap,"GB heap,", h2oPerNode, "jvm per host, import", protocol, "then parse"
                
                # jea = "-XX:+UseParNewGC -XX:+UseConcMarkSweepGC"
                # jea = "-Dh2o.find-ByteBuffer-leaks=true"
                h2o_hosts.build_cloud_with_hosts(h2oPerNode, java_heap_GB=tryHeap,
                    # java_extra_args=jea,
                    enable_benchmark_log=True, timeoutSecs=120, retryDelaySecs=10,
                    # all hdfs info is done thru the hdfs_config michal's ec2 config sets up?
                    # this is for our amazon ec hdfs
                    # see https://github.com/0xdata/h2o/wiki/H2O-and-s3n
                    hdfs_name_node='10.78.14.235:9000',
                    hdfs_version='0.20.2')

                # don't raise exception if we find something bad in h2o stdout/stderr?
                h2o.nodes[0].sandbox_ignore_errors = True

                for trial in range(trialMax):
                    # import a list of folders, one at a time (hdfs import can't take pattern match
                    # want to be able to parse 800 files, but only 200 per folder. Don't want to import the full bucket
                    # too slow
                    for csvFolder in csvFolderList:
                        if USE_S3:
                            URI = protocol + "://" + bucket  + "/" + csvFolder + "/"
                        else:
                            URI = protocol + "://" + bucket + "/" + csvFolder + "/"

                        # since we delete the key, we have to re-import every iteration, to get it again
                        # s3n URI thru HDFS is not typical.
                        if USE_S3:
                            importResult = h2o.nodes[0].import_s3(bucket)
                        else:
                            importResult = h2o.nodes[0].import_hdfs(URI)

                        s3nFullList = importResult['succeeded']
                        for k in s3nFullList:
                            key = k['key']
                            # just print the first tile
                            # if 'nflx' in key and 'file_1.dat.gz' in key: 
                            if csvFilepattern in key:
                                # should be s3n://home-0xdiag-datasets/manyfiles-nflx-gz/file_1.dat.gz
                                print "example file we'll use:", key
                                break
                            else:
                                ### print key
                                pass

                        ### print "s3nFullList:", h2o.dump_json(s3nFullList)
                        # error if none? 
                        self.assertGreater(len(s3nFullList),8,"Didn't see more than 8 files in s3n?")

                    s3nKey = csvFilepattern
                    key2 = csvFilename + "_" + str(trial) + ".hex"
                    print "Loading", protocol, "key:", s3nKey, "to", key2
                    start = time.time()
                    parseKey = h2o.nodes[0].parse(s3nKey, key2,
                        timeoutSecs=timeoutSecs, 
                        retryDelaySecs=retryDelaySecs,
                        pollTimeoutSecs=pollTimeoutSecs,
                        noPoll=noPoll,
                        benchmarkLogging=benchmarkLogging)

                    if noPoll:
                        if (i+1) < len(csvFilenameList):
                            time.sleep(1)
                            h2o.check_sandbox_for_errors()
                            (csvFilepattern, csvFilename, totalBytes2, timeoutSecs) = csvFilenameList[i+1]
                            s3nKey = URI + csvFilepattern
                            key2 = csvFilename + "_" + str(trial) + ".hex"
                            print "Loading", protocol, "key:", s3nKey, "to", key2
                            parse2Key = h2o.nodes[0].parse(s3nKey, key2,
                                timeoutSecs=timeoutSecs,
                                retryDelaySecs=retryDelaySecs,
                                pollTimeoutSecs=pollTimeoutSecs,
                                noPoll=noPoll,
                                benchmarkLogging=benchmarkLogging)

                        if (i+2) < len(csvFilenameList):
                            time.sleep(1)
                            h2o.check_sandbox_for_errors()
                            (csvFilepattern, csvFilename, totalBytes3, timeoutSecs) = csvFilenameList[i+2]
                            s3nKey = URI + csvFilepattern
                            key2 = csvFilename + "_" + str(trial) + ".hex"
                            print "Loading", protocol, "key:", s3nKey, "to", key2
                            parse3Key = h2o.nodes[0].parse(s3nKey, key2,
                                timeoutSecs=timeoutSecs, 
                                retryDelaySecs=retryDelaySecs,
                                pollTimeoutSecs=pollTimeoutSecs,
                                noPoll=noPoll,
                                benchmarkLogging=benchmarkLogging)

                    elapsed = time.time() - start
                    print s3nKey, 'parse time:', parseKey['response']['time']
                    print "parse result:", parseKey['destination_key']
                    print "Parse #", trial, "completed in", "%6.2f" % elapsed, "seconds.", \
                        "%d pct. of timeout" % ((elapsed*100)/timeoutSecs)

                    # print stats on all three if noPoll
                    if noPoll:
                        # does it take a little while to show up in Jobs, from where we issued the parse?
                        time.sleep(2)
                        # FIX! use the last (biggest?) timeoutSecs? maybe should increase since parallel
                        h2o_jobs.pollWaitJobs(pattern=csvFilename, 
                            timeoutSecs=timeoutSecs, benchmarkLogging=benchmarkLogging)
                        # for getting the MB/sec closer to 'right'
                        totalBytes += totalBytes2 + totalBytes3
                        elapsed = time.time() - start
                        h2o.check_sandbox_for_errors()

                    if totalBytes is not None:
                        fileMBS = (totalBytes/1e6)/elapsed
                        l = '{:d} jvms, {:d}GB heap, {:s} {:s} {:6.2f} MB/sec for {:6.2f} secs'.format(
                            len(h2o.nodes), tryHeap, csvFilepattern, csvFilename, fileMBS, elapsed)
                        print l
                        h2o.cloudPerfH2O.message(l)

                    # BUG here?
                    if not noPoll:
                        # We should be able to see the parse result?
                        h2o_cmd.check_enums_from_inspect(parseKey)

                    #**********************************************************************************
                    # Do GLM too
                    # Argument case error: Value 0.0 is not between 12.0 and 9987.0 (inclusive)
                    if DO_GLM or DO_GLMGRID:
                        # these are all the columns that are enums in the dataset...too many for GLM!
                        x = range(542) # don't include the output column
                        # remove the output too! (378)
                        for i in [3, 4, 5, 6, 7, 8, 9, 10, 11, 14, 16, 17, 18, 19, 20, 424, 425, 426, 540, 541, 378]:
                            x.remove(i)
                        x = ",".join(map(str,x))

                        if DO_GLM:
                            algo = 'GLM'
                            GLMkwargs = {'x': x, 'y': 378, 'case': 15, 'case_mode': '>', 'family': 'binomial',
                                'max_iter': 10, 'n_folds': 1, 'alpha': 0.2, 'lambda': 1e-5}
                            start = time.time()
                            glm = h2o_cmd.runGLMOnly(parseKey=parseKey, 
                                timeoutSecs=timeoutSecs, retryDelaySecs=retryDelaySecs,
                                pollTimeoutSecs=pollTimeoutSecs,
                                benchmarkLogging=benchmarkLogging, **GLMkwargs)
                            elapsed = time.time() - start
                            h2o_glm.simpleCheckGLM(self, glm, None, **GLMkwargs)

                        else:
                            algo = 'GLMGrid'
                            GLMkwargs = {'x': x, 'y': 378, 'case': 15, 'case_mode': '>', 'family': 'binomial',
                                'max_iter': 10, 'n_folds': 1, 'beta_epsilon': 1e-4,
                                'lambda': '1e-4',
                                'alpha': '0,0.5',
                                'thresholds': '0.5'
                                }
                            start = time.time()
                            glm = h2o_cmd.runGLMGridOnly(parseKey=parseKey,
                                timeoutSecs=timeoutSecs, retryDelaySecs=retryDelaySecs,
                                pollTimeoutSecs=pollTimeoutSecs,
                                benchmarkLogging=benchmarkLogging, **GLMkwargs)
                            elapsed = time.time() - start
                            h2o_glm.simpleCheckGLMGrid(self, glm, None, **GLMkwargs)

                        h2o.check_sandbox_for_errors()
                        l = '{:d} jvms, {:d}GB heap, {:s} {:s} {:s} {:6.2f} secs'.format(
                            len(h2o.nodes), tryHeap, algo, csvFilepattern, csvFilename, elapsed)
                        print l
                        h2o.cloudPerfH2O.message(l)

                    #**********************************************************************************
                    print "Deleting key in H2O so we get it from S3 (if ec2) or nfs again.", \
                          "Otherwise it would just parse the cached key."
                    ### storeView = h2o.nodes[0].store_view()
                    ### print "storeView:", h2o.dump_json(storeView)
                    # "key": "s3n://home-0xdiag-datasets/manyfiles-nflx-gz/file_84.dat.gz"
                    # have to do the pattern match ourself, to figure out what keys to delete
                    # we're deleting the keys in the initial import. We leave the keys we created
                    # by the parse. We use unique dest keys for those, so no worries.
                    # Leaving them is good because things fill up! (spill)
                    h2o_cmd.check_key_distribution()
                    h2o_cmd.delete_csv_key(csvFilename, s3nFullList)

                h2o.tear_down_cloud()
                # sticky ports? wait a bit.
                print "Waiting 30 secs before building cloud again (sticky ports?)"
                time.sleep(30)

if __name__ == '__main__':
    h2o.unit_main()

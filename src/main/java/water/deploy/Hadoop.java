package water.deploy;

import java.io.*;
import java.net.*;
import java.util.*;

import org.apache.hadoop.conf.Configuration;
import org.apache.hadoop.conf.Configured;
import org.apache.hadoop.io.*;
import org.apache.hadoop.mapred.JobClient;
import org.apache.hadoop.mapreduce.*;
import org.apache.hadoop.mapreduce.Job;
import org.apache.hadoop.util.Tool;
import org.apache.hadoop.util.ToolRunner;
import org.apache.log4j.Level;
import org.apache.log4j.Logger;

import water.*;
import water.api.*;
import water.api.RequestBuilders.Response.Status;
import water.api.RequestStatics.RequestType;
import water.api.Script.RunScript;
import water.api.Cloud;
import water.hdfs.HdfsLoader;
import water.util.Log;
import water.util.Utils;

import com.amazonaws.util.json.JSONObject;

public class Hadoop {
  public static class Config extends Arguments.Opt {
    String version = "cdh3";
    String user = "hduser";
    String name_server = "hdfs://127.0.0.1:8020";
    String tracker = "hdfs://127.0.0.1:8021";
    int port = 54321;
    String script;
  }

  public static void main(String[] args) throws Exception {
    Arguments arguments = new Arguments(args);
    Config config = new Config();
    arguments.extract(config);
    String[] remaining = new String[0];
    if( arguments.firstFlag() >= 0 ) remaining = Arrays.copyOfRange(args, arguments.firstFlag(), args.length);

    H2O.OPT_ARGS.hdfs_version = config.version;
    HdfsLoader.initialize();

    HadoopTool.main(config, remaining);
  }

  public static class HadoopTool extends Configured implements Tool {
    private static final String HOSTS_KEY = "h2o.hosts";
    private static final String PORT_KEY = "h2o.port";

    static class H2OMapper extends Mapper<LongWritable, Text, LongWritable, Text> {
      @Override protected void setup(Mapper.Context context) throws IOException, InterruptedException {
        try {
          String hosts = "";
          String port = context.getConfiguration().get(PORT_KEY);
          for( String host : context.getConfiguration().get(HOSTS_KEY).split(",") )
            hosts += host + ":" + port + '\n';
          File flat = Utils.tempFile(hosts);
          Boot.main(new String[] { "-name", "hadoop", "-port", port, "-flatfile", flat.getAbsolutePath() });
          for( ;; ) {
            // Report progress or task gets killed
            context.progress();
            Thread.sleep(10000);
          }
        } catch( Exception ex ) {
          throw Log.errRTExcept(ex);
        }
      }

      @Override protected void map(LongWritable key, Text value, Context context) throws IOException,
          InterruptedException {};
    }

    @Override public int run(String[] args) throws Exception {
      Job job = new Job(getConf());
      job.setJobName("H2O");
      job.setMapperClass(H2OMapper.class);
      job.setInputFormatClass(NopInputFormat.class);
      job.setOutputFormatClass(NopOutputFormat.class);
      job.setNumReduceTasks(0);
      job.submit();
      return 0;
    }

    private static class NopInputFormat extends InputFormat<Void, Void> {
      @Override public List<InputSplit> getSplits(JobContext context) throws IOException, InterruptedException {
        ArrayList<InputSplit> list = new ArrayList<InputSplit>();
        for( String host : context.getConfiguration().get(HOSTS_KEY).split(",") )
          list.add(new NopInputSplit(host));
        return list;
      }

      @Override public RecordReader<Void, Void> createRecordReader(InputSplit split, TaskAttemptContext context)
          throws IOException, InterruptedException {
        return new NopRecordReader();
      }
    }

    private static class NopOutputFormat extends OutputFormat<Void, Void> {
      @Override public RecordWriter<Void, Void> getRecordWriter(TaskAttemptContext context) throws IOException,
          InterruptedException {
        return new NopRecordWriter();
      }

      @Override public void checkOutputSpecs(JobContext context) throws IOException, InterruptedException {}

      @Override public OutputCommitter getOutputCommitter(TaskAttemptContext context) throws IOException,
          InterruptedException {
        return new NopOutputCommitter();
      }
    }

    private static class NopInputSplit extends InputSplit implements Writable {
      final String _loc;

      NopInputSplit(String loc) {
        _loc = loc;
      }

      @SuppressWarnings("unused") NopInputSplit() {
        _loc = null;
      }

      @Override public long getLength() throws IOException, InterruptedException {
        return 0;
      }

      @Override public String[] getLocations() throws IOException, InterruptedException {
        return new String[] { _loc };
      }

      @Override public void write(DataOutput out) throws IOException {}

      @Override public void readFields(DataInput in) throws IOException {}
    }

    private static class NopRecordReader extends RecordReader {
      @Override public void initialize(InputSplit split, TaskAttemptContext context) throws IOException,
          InterruptedException {}

      @Override public boolean nextKeyValue() throws IOException, InterruptedException {
        throw new RuntimeException("TODO Auto-generated method stub");
      }

      @Override public Object getCurrentKey() throws IOException, InterruptedException {
        throw new RuntimeException("TODO Auto-generated method stub");
      }

      @Override public Object getCurrentValue() throws IOException, InterruptedException {
        throw new RuntimeException("TODO Auto-generated method stub");
      }

      @Override public float getProgress() throws IOException, InterruptedException {
        throw new RuntimeException("TODO Auto-generated method stub");
      }

      @Override public void close() throws IOException {
        throw new RuntimeException("TODO Auto-generated method stub");
      }
    }

    private static class NopRecordWriter extends RecordWriter {
      @Override public void write(Object key, Object value) throws IOException, InterruptedException {
        throw new RuntimeException("TODO Auto-generated method stub");
      }

      @Override public void close(TaskAttemptContext context) throws IOException, InterruptedException {
        throw new RuntimeException("TODO Auto-generated method stub");
      }
    }

    static class NopOutputCommitter extends OutputCommitter {
      @Override public void setupJob(JobContext jobContext) throws IOException {}

      @Override public void setupTask(TaskAttemptContext taskContext) throws IOException {}

      @Override public boolean needsTaskCommit(TaskAttemptContext taskContext) throws IOException {
        return false;
      }

      @Override public void commitTask(TaskAttemptContext taskContext) throws IOException {}

      @Override public void abortTask(TaskAttemptContext taskContext) throws IOException {}
    }

    public static void main(Config config, String[] args) throws Exception {
      Logger.getRootLogger().setLevel(Level.ALL);
      System.setProperty("HADOOP_USER_NAME", config.user);
      Configuration conf = new Configuration();
      conf.set("fs.default.name", config.name_server);
      conf.set("mapred.job.tracker", config.tracker);
      conf.set("mapreduce.framework.name", "classic");
      // conf.set("hadoop.job.ugi", "hduser,hduser");
      conf.setInt("mapred.tasktracker.map.tasks.maximum", 1);
      conf.set("mapred.jar", "/home/cypof/h2o/target/h2o.jar");
      conf.set("mapred.child.java.opts", "-Xms256m -Xmx2g -XX:+UseSerialGC");
      conf.set("mapred.job.map.memory.mb", "4096");
      conf.set("mapred.job.reduce.memory.mb", "1024");
      conf.set("mapred.fairscheduler.locality.delay", "120000");
//      conf.set("fs.maprfs.impl", "com.mapr.fs.MapRFileSystem");

      String hosts = "";
      URI tracker = new URI(config.tracker);
      JobClient client = new JobClient(new InetSocketAddress(tracker.getHost(), tracker.getPort()), conf);
      Collection<String> names = client.getClusterStatus(true).getActiveTrackerNames();
      for( String name : names )
        hosts += name.substring("tracker_".length(), name.indexOf(':')) + ',';
      conf.set(HOSTS_KEY, hosts);
      conf.set(PORT_KEY, "" + config.port);

      ToolRunner.run(conf, new HadoopTool(), args);

      if( config.script != null ) {
        String url = "http://" + hosts.substring(0, hosts.indexOf(',')) + ":" + config.port + "/";
        // Wait for cloud to be up
        for( ;; ) {
          if( size(url) == names.size() ) break;
          Thread.sleep(300);
        }
        String res = post(url, config.script, 0);
        JSONObject json = new JSONObject(res);
        JSONObject resp = json.getJSONObject(Constants.RESPONSE);
        String status = resp.getString(Constants.STATUS);
        System.out.println("Status: " + status);
        if( status == Status.error.name() ) {
          System.out.println("Response: " + res);
        }
      }
    }

    public static int size(String url) {
      try {
        String cloud = Cloud.class.getSimpleName() + RequestType.json._suffix;
        HttpURLConnection c = (HttpURLConnection) new URL(url + cloud).openConnection();
        c.setConnectTimeout(2 * 1000);
        c.setReadTimeout(2 * 1000);
        c.connect();
        BufferedReader rd = new BufferedReader(new InputStreamReader(c.getInputStream()));
        String result = "", line;
        while( (line = rd.readLine()) != null )
          result += line;
        rd.close();
        JSONObject o = new JSONObject(result);
        int size = o.getInt(Constants.CLOUD_SIZE);
        return size;
      } catch( Exception ex ) {
        return 0;
      }
    }

    public static String post(String url, String file, float timeoutSecs) {
      try {
        File f = new File(file);
        String run = RunScript.class.getSimpleName() + RequestType.json._suffix + "?key=" + f.getName();
        HttpURLConnection c = (HttpURLConnection) new URL(url + run).openConnection();
        c.setDoOutput(true);
        c.setRequestMethod("POST");
        c.setConnectTimeout((int) (timeoutSecs * 1000));
        c.setReadTimeout((int) (timeoutSecs * 1000));
        String boundary = "683c3db71d444a2fbab155ba3e128d04";
        c.setRequestProperty("Content-Type", "multipart/form-data;boundary=" + boundary);
        c.connect();
        OutputStream out = c.getOutputStream();
        out.write(("--" + boundary + "\r\n").getBytes());
        out.write(("Content-Disposition: form-data; filename=\"" + f.getName() + "\"\r\n").getBytes());
        out.write("Content-Type: application/octet-stream\r\n".getBytes());
        out.write("\r\n".getBytes());

        byte[] buffer = new byte[0xffff];
        FileInputStream in = new FileInputStream(f);
        int n = 0;
        while( (n = in.read(buffer)) != -1 )
          out.write(buffer, 0, n);
        in.close();

        out.write(("\r\n--" + boundary + "--\r\n").getBytes());
        out.close();
        BufferedReader rd = new BufferedReader(new InputStreamReader(c.getInputStream()));
        String result = "", line;
        while( (line = rd.readLine()) != null )
          result += line;
        rd.close();
        return result;
      } catch( IOException ex ) {
        throw new RuntimeException(ex);
      } catch( Exception ex ) {
        throw Log.errRTExcept(ex);
      }
    }
  }
}
import java.io.BufferedReader;
import java.io.FileReader;
import java.io.PrintWriter;
import java.util.ArrayList;
import java.util.List;

import weka.classifiers.AbstractClassifier;
import weka.classifiers.Classifier;
import weka.core.Attribute;
import weka.core.Instances;
import weka.core.Utils;
import weka.core.Version;
import weka.core.converters.ConverterUtils.DataSource;

/**
 * Runs many WEKA train/test jobs inside ONE JVM (avoids ~1 s JVM start per job).
 *
 * jobs file: tab-separated lines
 *   job_name  train.arff  test.arff  out.csv  classifier_class  [classifier options...]
 *
 * Every job: class = LAST attribute, nominal {Absent,Present}. Train and test headers must be
 * equal (checked with Instances.equalHeadersMsg). Output CSV columns: row,p_present,pred,actual
 * where row is the 0-based row order of test.arff (Python keeps the matching patient IDs).
 */
public class WekaBatchRunner {
    public static void main(String[] args) throws Exception {
        if (args.length != 1) {
            System.err.println("usage: WekaBatchRunner jobs.tsv");
            System.exit(2);
        }
        System.out.println("WEKA version " + Version.VERSION);
        List<String[]> jobs = new ArrayList<>();
        try (BufferedReader br = new BufferedReader(new FileReader(args[0]))) {
            String line;
            while ((line = br.readLine()) != null) {
                if (line.isBlank() || line.startsWith("#")) continue;
                jobs.add(line.split("\t"));
            }
        }
        int done = 0;
        for (String[] j : jobs) {
            String name = j[0], trainPath = j[1], testPath = j[2], outPath = j[3], cls = j[4];
            String[] opts = j.length > 5 ? Utils.splitOptions(j[5]) : new String[0];
            Instances train = DataSource.read(trainPath);
            Instances test = DataSource.read(testPath);
            train.setClassIndex(train.numAttributes() - 1);
            test.setClassIndex(test.numAttributes() - 1);
            String msg = train.equalHeadersMsg(test);
            if (msg != null) throw new IllegalStateException(name + ": header mismatch: " + msg);
            Attribute ca = train.classAttribute();
            int pos = ca.indexOfValue("Present");
            if (pos < 0 || ca.numValues() != 2) throw new IllegalStateException(name + ": class must be {Absent,Present}");
            Classifier c = AbstractClassifier.forName(cls, opts.clone());
            long t0 = System.nanoTime();
            c.buildClassifier(train);
            long t1 = System.nanoTime();
            try (PrintWriter pw = new PrintWriter(outPath)) {
                pw.println("row,p_present,pred,actual");
                for (int i = 0; i < test.numInstances(); i++) {
                    double[] d = c.distributionForInstance(test.instance(i));
                    double pred = Utils.maxIndex(d);
                    String actual = test.instance(i).classIsMissing() ? "?" : ca.value((int) test.instance(i).classValue());
                    pw.printf(java.util.Locale.ROOT, "%d,%.10f,%s,%s%n", i, d[pos], ca.value((int) pred), actual);
                }
            }
            long t2 = System.nanoTime();
            done++;
            System.out.printf(java.util.Locale.ROOT, "job %s ok train=%d test=%d fit_s=%.3f predict_s=%.4f spec=%s%n",
                    name, train.numInstances(), test.numInstances(), (t1 - t0) / 1e9, (t2 - t1) / 1e9,
                    cls + " " + (j.length > 5 ? j[5] : ""));
        }
        System.out.println("completed " + done + "/" + jobs.size() + " jobs");
    }
}

import org.apache.jena.query.Dataset;
import org.apache.jena.query.Query;
import org.apache.jena.query.QueryFactory;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;

import org.gdd.sage.core.factory.SageAutoConfiguration;
import org.gdd.sage.core.factory.SageConfigurationFactory;
import org.gdd.sage.http.ExecutionStats;
import org.json.simple.JSONArray;
import org.json.simple.JSONObject;
import org.json.simple.parser.JSONParser;
import org.json.simple.parser.ParseException;
import picocli.CommandLine;

import java.io.*;
import java.text.MessageFormat;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@CommandLine.Command(name = "ssv", footer = "Copyright(c) 2017",
        description = "Generate a VoID summary over a Sage dataset")
public class SageJenaVoid implements Runnable {
    @CommandLine.Option(names = {"--time"}, description = "Display the the query execution time at the end")
    public boolean time = true;
    @CommandLine.Option(names = "dataset", description = "Dataset URI")
    String dataset = null;

    String format = "xml";

    @CommandLine.Option(names = "process", description = "Result folder, if set this wont execute SPARQL VoID queries but will only process result.xml files to provide a void.ttl file")
    String folder = null;

    private String voidUri = null;
    private String voidPath = null;

    public static void main(String... args) {
        new CommandLine(new SageJenaVoid()).execute(args);
    }

    @Override
    public void run() {
        if (folder != null) {
            mergeResultFile(folder);
        } else {
            if (dataset == null) {
                CommandLine.usage(this, System.out);
            } else {
                System.out.println("Executing the void on: " + dataset);
                this.voidUri = dataset; //dataset.replace('/', '_').replace(':', '_');
                // load the void queries
                JSONArray queries = loadVoidQueries(dataset);
                // Now execute queries by group
                executeVoidQueries(queries);
            }
        }

    }

    /**
     * Execute each VoID query
     *
     * @param queries
     */
    private void executeVoidQueries(JSONArray queries) {
        // create the result dir
        File file = new File(System.getProperty("user.dir"), this.voidUri);
        System.out.println("Output dir: " + file.getAbsolutePath());
        Boolean success = file.mkdirs();
        if (success) {
            System.out.println("Successfully created the output dir to: " + file.getAbsolutePath());
        } else {
            System.out.println("Output path already exists: " + file.getAbsolutePath());
        }

        ExecutorService executorService = Executors.newFixedThreadPool(50);
        List<Callable<JSONObject>> callables = new ArrayList<>();
        queries.forEach(bucket -> {
            JSONObject buc = (JSONObject) bucket;
            String group = (String) buc.get("group");
            String description = (String) buc.get("description");
            JSONArray arr = (JSONArray) buc.get("queries");
            System.out.println("Group: " + group + " Description: " + description);

            for (Object q : arr) {
                JSONObject queryJson = (JSONObject) q;
                String query = (String) queryJson.get("query");
                String label = (String) queryJson.get("label");
                System.out.println("[" + label + "] Execute query: " + query);
                try {
                    callables.add(new Callable<JSONObject>() {
                        @Override
                        public JSONObject call() throws Exception {
                            File queryFile = new File(file.getAbsolutePath(), label + "-result.xml");
                            FileOutputStream out = null;
                            try {
                                out = new FileOutputStream(queryFile);
                            } catch (FileNotFoundException e) {
                                e.printStackTrace();
                                System.exit(1);
                            }

                            JSONObject result = new JSONObject();
                            result.put("query", queryJson);
                            try{
                                executeVoidQuery(query, new PrintStream(out));
                                result.put("response", true);
                            } catch(Exception e) {
                                result.put("response", false);
                                result.put("error", e);
                            }
                            return result;
                        }
                    });
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        });

        JSONArray resultOfVoid = new JSONArray();
        try {
            List<Future<JSONObject>> futures = executorService.invokeAll(callables);
            int i = 0;
            for (Future<JSONObject> future : futures) {
                JSONObject result = future.get();
                resultOfVoid.add(result);
            }
        } catch (InterruptedException e) {
            e.printStackTrace();
        } catch (ExecutionException e) {
            e.printStackTrace();
        }

        // write the json modified into the
        File jsonOutput = new File(file.getAbsolutePath(), "result.json");
        try {
            resultOfVoid.writeJSONString(new FileWriter(jsonOutput));
        } catch (IOException e) {
            e.printStackTrace();
        }

        executorService.shutdown();
    }

    /**
     * Read all result files then output the summury into a void.ttl file in the generated output folder
     * The generated folder will contain all results as well as the json file used to generate results.
     */
    private void mergeResultFile(String folder) {
        File dir = new File(folder);
        File output = new File(dir.getAbsolutePath(), "void.ttl");
        File[] listOfFiles = dir.listFiles();

        Model m = ModelFactory.createDefaultModel();
        for (File file : listOfFiles) {
            if(file.getAbsolutePath().contains(".xml") && !file.getAbsolutePath().contains("QA")) {
                System.out.println("Processing: " + file.getAbsolutePath());
                Model tmp = ModelFactory.createDefaultModel();
                try {
                    tmp.read(new FileInputStream(file.getAbsoluteFile()), voidUri, "RDFXML");
                } catch (FileNotFoundException e) {
                    e.printStackTrace();
                }
                m.add(tmp);
            }
        }

        try {
            m.write(new FileOutputStream(output), "TURTLE");
        } catch (FileNotFoundException e) {
            e.printStackTrace();
        }
    }

    /**
     * Execute a SELECT VoID query over the sepecified dataset using Sage-Jena engine
     * This code is based on https://github.com/sage-org/sage-jena/blob/master/src/main/java/org/gdd/sage/cli/CLI.java
     *
     * @param queryString
     */
    private String executeVoidQuery(String queryString, PrintStream out) {
        String type;
        Dataset federation;
        SageConfigurationFactory factory;
        ExecutionStats spy = new ExecutionStats();

        Query parseQuery = QueryFactory.create(queryString);
        factory = new SageAutoConfiguration(dataset, parseQuery, spy);

        // Init Sage dataset (maybe federated)
        factory.configure();
        factory.buildDataset();
        parseQuery = factory.getQuery();
        federation = factory.getDataset();


        // Evaluate SPARQL query
        QueryExecutor executor;

        if (parseQuery.isSelectType()) {
            executor = new SelectQueryExecutor(format);
            type = "select";
        } else if (parseQuery.isConstructType()) {
            executor = new ConstructQueryExecutor(format);
            type = "construct";
        } else {
            throw new Error("Cannot parse the query: we only perform select or construct for generating voids");
        }
        spy.startTimer();
        executor.execute(format, federation, parseQuery, out);
        spy.stopTimer();

        if (this.time) {
            double duration = spy.getExecutionTime();
            int nbQueries = spy.getNbCalls();
            System.err.println(MessageFormat.format("SPARQL query executed in {0}s with {1} HTTP requests", duration, nbQueries));
        }

        // cleanup connections
        federation.close();
        factory.close();
        return type;
    }

    /**
     * Generate VoID queries withing the dataset specified
     *
     * @param dataset the dataset where we will generate queries
     * @return
     */
    JSONArray loadVoidQueries(String dataset) {
        // load the json file
        JSONObject file = loadJSONFile("data/sportal.json");
        String uri = (String) file.get("datasetUri");
        JSONArray voID = (JSONArray) file.get("void");
        // dataset domain
        voID.forEach(bucket -> {
            JSONObject buc = (JSONObject) bucket;
            JSONArray queries = (JSONArray) buc.get("queries");
            for (Object q : queries) {
                JSONObject queryJson = (JSONObject) q;
                String query = (String) queryJson.get("query");
                // System.out.println("Replacing " + uri + " by " + voidUri);
                query = query.replaceAll(uri, voidUri);
                queryJson.put("query", query);
            }
        });
        return voID;
    }


    /**
     * Load a JSON file as a string, the file must begins by an Object (JSONObject)
     *
     * @param file
     * @return
     */
    JSONObject loadJSONFile(String file) {
        //JSON parser object to parse read file
        JSONParser jsonParser = new JSONParser();

        try (FileReader reader = new FileReader(file)) {
            //Read JSON file
            Object obj = jsonParser.parse(reader);

            JSONObject queries = (JSONObject) obj;

            return queries;
        } catch (FileNotFoundException e) {
            e.printStackTrace();
            System.exit(1);
        } catch (IOException e) {
            e.printStackTrace();
            System.exit(1);
        } catch (ParseException e) {
            e.printStackTrace();
            System.exit(1);
        }
        return null;
    }

    /**
     * Determine if the string is an url
     *
     * @param s
     * @return
     */
    private boolean isURL(String s) {
        try {
            Pattern pattern = Pattern.compile("^(https?|ftp|file)://[-a-zA-Z0-9+&@#/%?=~_|!:,.;]*[-a-zA-Z0-9+&@#/%=~_|]");
            Matcher matcher = pattern.matcher(s);
            return matcher.matches();
        } catch (RuntimeException e) {
            return false;
        }
    }
}

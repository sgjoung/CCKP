import java.io.BufferedReader;
import java.io.FileReader;
import java.io.IOException;

public class readdata {
	int n;
	double[] K;
	double[] b;
	double[][] c, a;
	int num;
	double[] zstar, zL;
	double[] timeZstar, timeZL;
	
	public void readdata(String file, int n){
		String defaultFile = "data/cckp_test_set_" + n + ".csv";
		String csvFile = (file == null || file.isBlank()) ? defaultFile : file;
        String line;
        String csvSplitBy = ",";

        int numRows = (n <= 100) ? 100 : 10;
        c = new double[numRows][];
        a = new double[numRows][];
        b = new double[numRows];
        K = new double[numRows];
        zstar = new double[numRows];
        zL = new double[numRows];
        timeZstar = new double[numRows];
        timeZL = new double[numRows];
        
        this.n = n;
        
        try (BufferedReader br = new BufferedReader(new FileReader(csvFile))) {
            int rowIndex = 0;

            while ((line = br.readLine()) != null && rowIndex < numRows) {
                
                String[] fields = line.split(csvSplitBy);
                int expectedCols = 2 * n + 6; // c[n], a[n], b, K, zstar, zL, timeZstar, timeZL
                if (fields.length < expectedCols) {
                	throw new IllegalArgumentException(
                			"Invalid CSV format in " + csvFile + " at row " + (rowIndex + 1)
                					+ ": expected at least " + expectedCols + " columns, got " + fields.length);
                }
                
                c[rowIndex] = new double[n];
                a[rowIndex] = new double[n];
                
                int loc = 0;
                for (int i = 0; i < n; i++) {
                    c[rowIndex][i] = Integer.parseInt(fields[loc]);
                    loc++;
                }
                for (int i = 0; i < n; i++) {
                    a[rowIndex][i] = Integer.parseInt(fields[loc]);
                    loc++;
                }
                b[rowIndex] = Double.parseDouble(fields[loc]);
                loc ++;
                K[rowIndex] = Double.parseDouble(fields[loc]);
                loc ++;
                zstar[rowIndex] = Double.parseDouble(fields[loc]);
                loc ++;
                zL[rowIndex] = Double.parseDouble(fields[loc]);
                loc ++;

                // Time columns are mandatory in this repository's dataset format.
                timeZstar[rowIndex] = Double.parseDouble(fields[loc]);
                loc++;
                timeZL[rowIndex] = Double.parseDouble(fields[loc]);
                loc++;
                
                rowIndex++;
            }
        } catch (IOException e) {
        	throw new RuntimeException("Failed to read CSV: " + csvFile, e);
        }
	}

	public int getn() {
		return n;
	}
	public double[][] getc(){
		return c;
	}
	public double[][] geta(){
		return a;
	}
	public double[] getb() {
		return b;
	}
	public double[] getK() {
		return K;
	}
	public double[] getzstar() {
		return zstar;
	}
	public double[] getzL() {
		return zL;
	}
	public double[] getTimeZstar() {
		return timeZstar;
	}
	public double[] getTimeZL() {
		return timeZL;
	}
	}

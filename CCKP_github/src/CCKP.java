import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.Locale;

import ilog.concert.IloException;
import ilog.concert.IloLinearNumExpr;
import ilog.concert.IloNumVar;
import ilog.concert.IloNumVarType;
import ilog.cplex.IloCplex;

/**
 * CCKP solver + experiment runner.
 *
 * <p>This class runs a set of instances loaded from a CSV file (see {@link readdata}) and appends
 * aggregated metrics to JSON result files.
 */
public class CCKP {
	int n;
	double[] K;
	double[] b;
	double[][] c, a;
	int num;
	double[] zstar, zL;

	double avggap = 0;
	double avggap2=0;
	double[] gap;
	double avgiter = 0;
	double avgcut = 0;

	public CCKP(int n, double[] K, double[] b, double[][] c, double[][] a, double[] zstar, double[] zL) {
		this.n = n;
		this.K = K;

		
		this.b = b;
		this.c = c;
		this.a = a;
		this.zstar = zstar;
		this.zL = zL;
		num = (n <= 100) ? 100 : 10;
		gap = new double[num];
	}

	public CCKP(int n, double[] K, double[] b, double[][] c, double[][] a, double[] zstar, double[] zL, double[] timeZstar,
			double[] timeZL) {
		this(n, K, b, c, a, zstar, zL);
		this.timeZstar = timeZstar;
		this.timeZL = timeZL;
	}

	double[] timeZstar, timeZL;

	private IloNumVar[] buildBaseModel(IloCplex cplex, int index) throws IloException {
		IloNumVar[] x = new IloNumVar[n];
		for (int i = 0; i < n; i++) {
			x[i] = cplex.numVar(0, 1, IloNumVarType.Float);
		}

		IloLinearNumExpr obj = cplex.linearNumExpr();
		for (int i = 0; i < n; i++) {
			obj.addTerm(c[index][i], x[i]);
		}
		cplex.addMaximize(obj);

		IloLinearNumExpr const1 = cplex.linearNumExpr();
		for (int i = 0; i < n; i++) {
			const1.addTerm(a[index][i], x[i]);
		}
		cplex.addLe(const1, b[index]);

		IloLinearNumExpr const2 = cplex.linearNumExpr();
		for (int i = 0; i < n; i++) {
			const2.addTerm(1, x[i]);
		}
		cplex.addLe(const2, K[index]);

		return x;
	}

	private static String fmt2(double v) {
		return String.format(Locale.US, "%.2f", v);
	}

	private static double averagePrefix(double[] arr, int len) {
		if (arr == null || len <= 0) {
			return 0.0;
		}
		double sum = 0.0;
		int k = Math.min(len, arr.length);
		for (int i = 0; i < k; i++) {
			sum += arr[i];
		}
		return sum / k;
	}

	private static double timeLimitSecondsForN(int n) {
		return (n <= 100) ? 300.0 : 3600.0;
	}

	/** Sets CPLEX time limit to the remaining budget for this instance. */
	private static void setRemainingTime(IloCplex cplex, long instStart, double limitSec) throws IloException {
		double rem = Math.max(0.0, limitSec - (System.currentTimeMillis() - instStart) / 1000.0);
		cplex.setParam(IloCplex.DoubleParam.TiLim, rem);
	}

	/** Same as {@link #setRemainingTime(IloCplex, long, double)} but for the subproblem CPLEX object. */
	private static void setRemainingTimeSub(IloCplex sub, long instStart, double limitSec) throws IloException {
		double rem = Math.max(0.0, limitSec - (System.currentTimeMillis() - instStart) / 1000.0);
		sub.setParam(IloCplex.DoubleParam.TiLim, rem);
	}

	/**
	 * Appends one JSON object into a JSON array file.
	 *
	 * <p>The file format is intentionally simple to avoid extra dependencies (Gson/Jackson).
	 */
	private static void appendJsonArray(String filename, String jsonObject) throws IOException {
		Path path = Path.of(filename);
		if (!Files.exists(path)) {
			String init = "[\n" + jsonObject + "\n]\n";
			Files.writeString(path, init, StandardCharsets.UTF_8, StandardOpenOption.CREATE);
			return;
		}
		String existing = Files.readString(path, StandardCharsets.UTF_8).trim();
		if (existing.isEmpty()) {
			String init = "[\n" + jsonObject + "\n]\n";
			Files.writeString(path, init, StandardCharsets.UTF_8, StandardOpenOption.TRUNCATE_EXISTING);
			return;
		}
		int idx = existing.lastIndexOf(']');
		if (idx < 0) {
			String init = "[\n" + jsonObject + "\n]\n";
			Files.writeString(path, init, StandardCharsets.UTF_8, StandardOpenOption.TRUNCATE_EXISTING);
			return;
		}
		String before = existing.substring(0, idx).trim();
		String after = existing.substring(idx);
		StringBuilder out = new StringBuilder(existing.length() + jsonObject.length() + 8);
		if (before.endsWith("[")) {
			out.append(before).append("\n").append(jsonObject).append("\n").append(after).append("\n");
		} else {
			out.append(before).append(",\n").append(jsonObject).append("\n").append(after).append("\n");
		}
		Files.writeString(path, out.toString(), StandardCharsets.UTF_8, StandardOpenOption.TRUNCATE_EXISTING);
	}

	public double greedy_cp() throws IloException, IOException {

		long start = System.currentTimeMillis();
		double limitSec = timeLimitSecondsForN(n);
		int timeouts = 0;
		double avgRelGap = 0.0; // (zL-obj)/zL
		for(int index = 0; index < num; index++) {
			long instStart = System.currentTimeMillis();
			IloCplex cplex = new IloCplex();
			IloNumVar[] x = buildBaseModel(cplex, index);


			cplex.setOut(null);

			int count = 0;

			setRemainingTime(cplex, instStart, limitSec);
			cplex.solve();


			while(count < 100) {

				count ++;


				double[] xval = cplex.getValues(x);


				double[] value = new double[n];
				for(int i=0; i<n; i++) {
					value[i] = xval[i]+0.0001*a[index][i];
				}

				int[] sorted_index = argsort(value);

				int[] alpha = new int[n];
				int[] beta = new int[n];

				double minf = Double.MAX_VALUE;
				double delta = b[index];

				int added = 0;
				for(int i=0 ; i<n; i++) {
					if(added == K[index])	break;
					else {
						if(delta - a[index][sorted_index[i]] > 0) {
							alpha[sorted_index[i]] = 1;
							delta = delta - a[index][sorted_index[i]];
							if(minf > a[index][sorted_index[i]])	minf = a[index][sorted_index[i]];
							added = added + 1;
						}
					}
				}
				for(int i=0; i<n; i++) {
					if(alpha[i] < 0.5 && a[index][i] <= minf) {
						beta[i] = 1;
					}
				}

				boolean equal = true;
				for(int i=0; i<n-1; i++) {
					if(a[index][i] != a[index][i+1])	equal = false;
				}
				if(added == K[index] && delta > 0 && !equal) {
					IloLinearNumExpr validcut = cplex.linearNumExpr();

					double lhsval = 0;

					for(int i=0; i<n; i++) {
						if(alpha[i] + beta[i] > 0.5) {
							validcut.addTerm(a[index][i] + delta, x[i]);
							lhsval += (a[index][i] + delta) * xval[i];
							a[index][i] = a[index][i] + delta;
						}
						else {
							validcut.addTerm(a[index][i], x[i]);
							lhsval += a[index][i] * xval[i];
						}
					}
					double rhsval = b[index] + (K[index] - 1) * delta;
					b[index] = b[index] + (K[index] - 1) * delta;
					cplex.addLe(validcut, rhsval);


					setRemainingTime(cplex, instStart, limitSec);
					cplex.solve();
				}
				else {
					break;
				}


			}
			gap[index] = 1- (cplex.getObjValue() - zstar[index])/(zL[index] - zstar[index]);
			avgRelGap += (zL[index] - cplex.getObjValue()) / zL[index];
			avggap += 1 - (cplex.getObjValue() - zstar[index])/(zL[index] - zstar[index]);
			avggap2 += Math.pow(1 - (cplex.getObjValue() - zstar[index])/(zL[index] - zstar[index]),2);
			avgiter += count;

			if ((System.currentTimeMillis() - instStart) / 1000.0 >= limitSec) {
				timeouts++;
			}
			cplex.end();


		}
		long end = System.currentTimeMillis();
		avggap = avggap / (double)num;
		avggap2 = avggap2 / (double)num;
		avgRelGap = avgRelGap / (double)num;

		double avgZstar = averagePrefix(zstar, num);
		double avgZL = averagePrefix(zL, num);
		double avgTzstar = averagePrefix(timeZstar, num);
		double avgTzL = averagePrefix(timeZL, num);
		double timeAvg = ((end - start) / 1000.0) / (double) num;
		double stdv = Math.sqrt(avggap2 - avggap * avggap);
		String json = "{"
				+ "\"method\":\"greedy_cp\""
				+ ",\"n\":" + n
				+ ",\"reduced_gap_avg\":" + avggap
				+ ",\"reduced_gap_stdv\":" + stdv
				+ ",\"time_avg_sec\":" + timeAvg
				+ ",\"iteration_avg\":" + (avgiter / (double) num)
				+ ",\"timeouts\":" + timeouts
				+ ",\"rel_gap_avg\":" + avgRelGap
				+ ",\"avg_zstar\":" + avgZstar
				+ ",\"avg_zl\":" + avgZL
				+ ",\"avg_time_zstar\":" + avgTzstar
				+ ",\"avg_time_zl\":" + avgTzL
				+ "}";
		appendJsonArray("result_heur_maximal.json", json);

		return avggap;
	}


	public double violation_max_cp() throws IloException, IOException {
		long start = System.currentTimeMillis();
		// For violation_max_cp: enforce 3600s overall per instance regardless of n.
		double limitSec = 3600.0;
		int timeouts = 0;
		double avgRelGap = 0.0; // (zL-obj)/zL
		for(int index = 0; index < num; index++) {
			long innerstart = System.currentTimeMillis();

			try (IloCplex cplex = new IloCplex()) {
				IloNumVar[] x = buildBaseModel(cplex, index);


				cplex.setOut(null);

				int count = 0;

				setRemainingTime(cplex, innerstart, limitSec);
				cplex.solve();


				while(count < 1000) {

					count ++;

					double[] xval = cplex.getValues(x);


					double[] alpha = new double[n];
					double[] beta = new double[n];

					double delta = b[index];



					try (IloCplex sub = new IloCplex()) {
						IloNumVar[] varalpha = new IloNumVar[n];
						IloNumVar[] varbeta = new IloNumVar[n];

						IloNumVar vardelta = sub.numVar(0, Double.MAX_VALUE, "delta");

						IloNumVar[] varu = new IloNumVar[n];
						IloNumVar[] varv = new IloNumVar[n];

						for(int i=0; i<n; i++) {
							varalpha[i] = sub.numVar(0, 1, IloNumVarType.Int, "alpha");
							varbeta[i] = sub.numVar(0, 1, IloNumVarType.Int, "beta");
							varu[i] = sub.numVar(0, Double.MAX_VALUE, IloNumVarType.Float, "u");
							varv[i] = sub.numVar(0, Double.MAX_VALUE, IloNumVarType.Float, "v");
						}

						IloLinearNumExpr subobj = sub.linearNumExpr();
						for(int i=0; i<n; i++) {
							subobj.addTerm(xval[i], varu[i]);
							subobj.addTerm(xval[i], varv[i]);
						}
						subobj.addTerm(-(K[index]-1), vardelta);

						for(int i=0; i<n; i++) {
							subobj.addTerm(0.00001*a[index][i], varalpha[i]);
							//					subobj.addTerm(0.00001*a[index][i], varbeta[i]);
						}

						sub.addMaximize(subobj);

						double[] a_for_sort = new double[n];
						for(int i=0; i<n; i++) {
							a_for_sort[i] = a[index][i];
						}

						int[] sorted_index = argsort(a_for_sort);


						IloLinearNumExpr subconst1 = sub.linearNumExpr();
						for(int i=0; i<n; i++) {
							subconst1.addTerm(1, varalpha[i]);
						}
						sub.addEq(subconst1, K[index]);

						IloLinearNumExpr[] subconst2 = new IloLinearNumExpr[n];
						for(int i=0; i<n; i++) {
							subconst2[i] = sub.linearNumExpr();
							subconst2[i].addTerm(1, varalpha[i]);
							subconst2[i].addTerm(1, varbeta[i]);
							sub.addLe(subconst2[i], 1);
						}

						IloLinearNumExpr[] subconst3_1 = new IloLinearNumExpr[n];

						for(int i=0; i<n; i++) {
							subconst3_1[i] = sub.linearNumExpr();
							subconst3_1[i].addTerm(1, varbeta[sorted_index[i]]);
							for(int j=0; j<=i-1; j++) {
								subconst3_1[i].addTerm(-1, varalpha[sorted_index[j]]);
							}
							sub.addGe(subconst3_1[i], -K[index]+1);
						}

						IloLinearNumExpr[] subconst3_2 = new IloLinearNumExpr[n];

						for(int i=0; i<n; i++) {
							subconst3_2[i] = sub.linearNumExpr();
							subconst3_2[i].addTerm(K[index], varbeta[sorted_index[i]]);
							for(int j=0; j<=i-1; j++) {
								subconst3_2[i].addTerm(-1, varalpha[sorted_index[j]]);
							}
							sub.addLe(subconst3_2[i], 0);
						}

						IloLinearNumExpr subconst4 = sub.linearNumExpr();
						subconst4.addTerm(1, vardelta);
						for(int i=0; i<n; i++) {
							subconst4.addTerm(a[index][i], varalpha[i]);
						}
						sub.addEq(subconst4, b[index]);

						IloLinearNumExpr[] subconst5 = new IloLinearNumExpr[n];
						IloLinearNumExpr[] subconst6 = new IloLinearNumExpr[n];
						IloLinearNumExpr[] subconst7 = new IloLinearNumExpr[n];
						IloLinearNumExpr[] subconst8 = new IloLinearNumExpr[n];



						for(int i=0; i<n; i++) {
							subconst5[i] = sub.linearNumExpr();
							subconst5[i].addTerm(1, varu[i]);
							subconst5[i].addTerm(-b[index], varalpha[i]);
							sub.addLe(subconst5[i], 0);

							subconst6[i] = sub.linearNumExpr();
							subconst6[i].addTerm(1, varu[i]);
							subconst6[i].addTerm(-1, vardelta);
							subconst6[i].addTerm(-b[index], varalpha[i]);
							sub.addGe(subconst6[i], -b[index]);

							subconst7[i] = sub.linearNumExpr();
							subconst7[i].addTerm(1, varv[i]);
							subconst7[i].addTerm(-b[index], varbeta[i]);
							sub.addLe(subconst7[i], 0);

							subconst8[i] = sub.linearNumExpr();
							subconst8[i].addTerm(1, varv[i]);
							subconst8[i].addTerm(-1, vardelta);
							subconst8[i].addTerm(-b[index], varbeta[i]);
							sub.addGe(subconst8[i], -b[index]);
						}

						IloLinearNumExpr[] subconst9 = new IloLinearNumExpr[n];
						IloLinearNumExpr[] subconst10 = new IloLinearNumExpr[n];
						IloLinearNumExpr[] subconst11 = new IloLinearNumExpr[n];
						IloLinearNumExpr[] subconst12 = new IloLinearNumExpr[n];



						for(int i=0; i<n; i++) {
							subconst9[i] = sub.linearNumExpr();
							subconst9[i].addTerm(1, varu[i]);
							subconst9[i].addTerm(b[index], varalpha[i]);
							sub.addGe(subconst9[i], 0);

							subconst10[i] = sub.linearNumExpr();
							subconst10[i].addTerm(1, varu[i]);
							subconst10[i].addTerm(-1, vardelta);
							subconst10[i].addTerm(b[index], varalpha[i]);
							sub.addLe(subconst10[i], b[index]);

							subconst11[i] = sub.linearNumExpr();
							subconst11[i].addTerm(1, varv[i]);
							subconst11[i].addTerm(b[index], varbeta[i]);
							sub.addGe(subconst11[i], 0);

							subconst12[i] = sub.linearNumExpr();
							subconst12[i].addTerm(1, varv[i]);
							subconst12[i].addTerm(-1, vardelta);
							subconst12[i].addTerm(b[index], varbeta[i]);
							sub.addLe(subconst12[i], b[index]);
						}

						sub.setOut(null);
						setRemainingTimeSub(sub, innerstart, limitSec);
						if (sub.solve()) {
							alpha = sub.getValues(varalpha);
							beta = sub.getValues(varbeta);
							delta = sub.getValue(vardelta);
						}
						
						double minf = Double.MAX_VALUE;

						for(int i=0 ; i<n; i++) {
							if(alpha[i] > 0.5) {
								if(minf > a[index][i])	minf = a[index][i];
							}
						}
						for(int i=0; i<n; i++) {
							if(alpha[i] < 0.5 && a[index][i] <= minf) {
								beta[i] = 1;
							}
						}



						sub.end();
						}

					boolean equal = true;
					for(int i=0; i<n-1; i++) {
						if(a[index][i] != a[index][i+1])	equal = false;
					}

					if(delta > 0 && !equal) {
						IloLinearNumExpr validcut = cplex.linearNumExpr();

						double lhsval = 0;

						for(int i=0; i<n; i++) {
							if(alpha[i] + beta[i] > 0.5) {
								validcut.addTerm(a[index][i] + delta, x[i]);
								lhsval += (a[index][i] + delta) * xval[i];
								a[index][i] = a[index][i] + delta;
							}
							else {
								validcut.addTerm(a[index][i], x[i]);
								lhsval += a[index][i] * xval[i];
							}
						}
						double rhsval = b[index] + (K[index] - 1) * delta;
						b[index] = b[index] + (K[index] - 1) * delta;
						cplex.addLe(validcut, rhsval);


						setRemainingTime(cplex, innerstart, limitSec);
						cplex.solve();
						
					}
					else {
						break;
					}


					//				if(lhsval > rhsval + 1e-6) {
					//					cplex.addLe(validcut, rhsval);
					//				}
					//				else {
					//					break;
					//				}


				}

				gap[index] = 1- (cplex.getObjValue() - zstar[index])/(zL[index] - zstar[index]);
				avgRelGap += (zL[index] - cplex.getObjValue()) / zL[index];
				avggap += 1 - (cplex.getObjValue() - zstar[index])/(zL[index] - zstar[index]);
				avggap2 += Math.pow(1 - (cplex.getObjValue() - zstar[index])/(zL[index] - zstar[index]),2);
				avgiter += count;

				if ((System.currentTimeMillis() - innerstart) / 1000.0 >= limitSec) {
					timeouts++;
				}
				cplex.end();
			}


		}
		long end = System.currentTimeMillis();
		avggap = avggap / (double)num;
		avggap2 = avggap2 / (double)num;
		avgRelGap = avgRelGap / (double)num;
		double avgZstar = averagePrefix(zstar, num);
		double avgZL = averagePrefix(zL, num);
		double avgTzstar = averagePrefix(timeZstar, num);
		double avgTzL = averagePrefix(timeZL, num);
		double timeAvg = ((end - start) / 1000.0) / (double) num;
		double stdv = Math.sqrt(avggap2 - avggap * avggap);
		String json = "{"
				+ "\"method\":\"violation_max_cp\""
				+ ",\"n\":" + n
				+ ",\"reduced_gap_avg\":" + avggap
				+ ",\"reduced_gap_stdv\":" + stdv
				+ ",\"time_avg_sec\":" + timeAvg
				+ ",\"iteration_avg\":" + (avgiter / (double) num)
				+ ",\"timeouts\":" + timeouts
				+ ",\"rel_gap_avg\":" + avgRelGap
				+ ",\"avg_zstar\":" + avgZstar
				+ ",\"avg_zl\":" + avgZL
				+ ",\"avg_time_zstar\":" + avgTzstar
				+ ",\"avg_time_zl\":" + avgTzL
				+ "}";
		appendJsonArray("result_violation_max.json", json);
		return avggap;
	}

	public static int[] argsort(double[] input) {
		int h = input.length;
		int[] index = new int[h];

		for (int i = 0; i < h; ++i)
			index[i] = i;

		for (int i = h - 1; i > 0; --i) {
			int min = 0;
			for (int j = 1; j <= i; ++j)
				if (input[index[j]] < input[index[min]])
					min = j;

			int temp = index[i];
			index[i] = index[min];
			index[min] = temp;
		}

		return index;
	}
}

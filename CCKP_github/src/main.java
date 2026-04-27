import java.io.IOException;

import ilog.concert.IloException;

/**
 * Entry point.
 *
 * <p>Defaults are defined in-code for convenience. You can override them via CLI arguments:
 * {@code java main <csv_file> <n> <method>} where method is {@code violation_max_cp} or {@code greedy_cp}.
 */
public class main {
	public static void main(String[] args) throws IloException, IOException {
		// Default run configuration (used when args are omitted).
		final String defaultFile = "data/cckp_test_set_50.csv";
		final int defaultN = 50;
		final String defaultMethod = "violation_max_cp";

		// CLI override order: file, n, method.
		String file = defaultFile;
		int n = defaultN;
		String method = defaultMethod;

		if (args != null) {
			if (args.length >= 1 && args[0] != null && !args[0].isBlank()) {
				file = args[0].trim();
			}
			if (args.length >= 2 && args[1] != null && !args[1].isBlank()) {
				n = Integer.parseInt(args[1].trim());
			}
			if (args.length >= 3 && args[2] != null && !args[2].isBlank()) {
				method = args[2].trim();
			}
		}

		readdata input = new readdata();
		input.readdata(file, n);
		CCKP prob = new CCKP(
				input.getn(),
				input.getK(),
				input.getb(),
				input.getc(),
				input.geta(),
				input.getzstar(),
				input.getzL(),
				input.getTimeZstar(),
				input.getTimeZL());
		// Execute only one method per run (each method appends to its own JSON result file).
		if ("violation_max_cp".equals(method)) {
			// Solve the CCKP problem using the violation_max_cp method
			prob.violation_max_cp();
		} else if ("greedy_cp".equals(method)) {
			// Solve the CCKP problem using the greedy_cp method
			prob.greedy_cp();
		} else {
			throw new IllegalArgumentException("Unknown method: " + method
					+ " (expected: violation_max_cp or greedy_cp)");
		}
	}
}

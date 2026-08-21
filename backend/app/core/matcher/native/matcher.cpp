/*
 * RECON-MESH Native C++ High-Throughput Heuristic Matching Kernel (Step 04)
 *
 * Compiled via PyBind11 as a Python extension module (`matcher_native`).
 * Processes 10,000+ transactions in <30ms using unordered_map UTR hash indexing
 * with zero GC pauses and exact integer paise arithmetic.
 *
 * Build:  python backend/app/core/matcher/native/setup.py build_ext --inplace
 * Toggle: NATIVE_MATCHER=true (env var) to activate; engine_factory.py auto-discovers the .so/.pyd
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace py = pybind11;

// ---------------------------------------------------------------------------
// Data Structures
// ---------------------------------------------------------------------------

/**
 * Lightweight canonical representation of a single financial transaction,
 * carrying only the fields required by the native matching kernel.
 */
struct NativeTransaction {
    std::string id;               // Canonical transaction ID (rzp/bank)
    std::string utr;              // Unique Transaction Reference (may be empty)
    int64_t     amount_net_paise; // Exact net credit/payment amount in paise
    int64_t     timestamp_sec;    // Unix epoch seconds (UTC)
    std::string batch_id;         // settlement_batch_id metadata (for 1:N grouping)
};

/**
 * Immutable result of a single successful match between one Razorpay and one Bank transaction.
 */
struct NativeMatchResult {
    std::string rzp_id;            // Matched Razorpay canonical ID
    std::string bank_id;           // Matched Bank canonical ID
    int64_t     match_amount_paise; // Verified match amount in paise
    int64_t     time_delta_sec;    // Absolute time difference in seconds
};

/**
 * Batch match result: a single bank entry matched to N Razorpay transactions.
 */
struct NativeBatchMatchResult {
    std::vector<std::string> rzp_ids;     // All Razorpay canonical IDs in the batch
    std::string              bank_id;     // Matched Bank canonical ID
    int64_t                  total_amount_paise; // Aggregate net paise sum
};

// ---------------------------------------------------------------------------
// NativeHeuristicMatcher
// ---------------------------------------------------------------------------

/**
 * High-throughput heuristic matching kernel.
 *
 * Stage 1A: 1:1 UTR + exact integer paise + time window match.
 * Stage 1B: 1:N batch settlement match via batch_id grouping + sum comparison.
 */
class NativeHeuristicMatcher {
public:
    explicit NativeHeuristicMatcher(int64_t time_window_sec = 259200LL) // 72 hours
        : time_window_sec_(time_window_sec) {}

    /**
     * Stage 1A — Strict 1:1 matching:
     *   RZP.utr == Bank.utr  AND
     *   RZP.amount_net_paise == Bank.amount_net_paise  AND
     *   |RZP.timestamp_sec - Bank.timestamp_sec| <= time_window_sec
     *
     * Returns vector of NativeMatchResult for every matched pair.
     */
    std::vector<NativeMatchResult> match_1to1(
        const std::vector<NativeTransaction>& rzp_txns,
        const std::vector<NativeTransaction>& bank_txns
    ) {
        std::vector<NativeMatchResult> results;
        results.reserve(std::min(rzp_txns.size(), bank_txns.size()));

        // Build O(1) UTR hash index on bank entries
        // Maps: utr -> list of indices into bank_txns
        std::unordered_map<std::string, std::vector<size_t>> bank_utr_index;
        bank_utr_index.reserve(bank_txns.size());
        for (size_t i = 0; i < bank_txns.size(); ++i) {
            if (!bank_txns[i].utr.empty()) {
                bank_utr_index[bank_txns[i].utr].push_back(i);
            }
        }

        std::vector<bool> bank_used(bank_txns.size(), false);

        // Linear scan over Razorpay transactions — O(N) with O(1) lookup per UTR
        for (const auto& rzp : rzp_txns) {
            if (rzp.utr.empty()) {
                continue;
            }

            auto it = bank_utr_index.find(rzp.utr);
            if (it == bank_utr_index.end()) {
                continue;
            }

            for (size_t b_idx : it->second) {
                if (bank_used[b_idx]) {
                    continue;
                }

                const auto& bank = bank_txns[b_idx];

                if (bank.amount_net_paise != rzp.amount_net_paise) {
                    continue;
                }

                int64_t t_delta = std::abs(bank.timestamp_sec - rzp.timestamp_sec);
                if (t_delta > time_window_sec_) {
                    continue;
                }

                bank_used[b_idx] = true;
                results.push_back({
                    rzp.id,
                    bank.id,
                    rzp.amount_net_paise,
                    t_delta
                });
                break; // First valid match wins — greedy
            }
        }

        return results;
    }

    /**
     * Stage 1B — 1:N batch settlement matching:
     *   Groups all RZP transactions by batch_id.
     *   For each batch: SUM(rzp.amount_net_paise) must equal exactly one Bank credit.
     *   Respects time window against the latest RZP timestamp in the batch.
     *
     * Returns vector of NativeBatchMatchResult (one per settled batch).
     * Populates matched_rzp_ids and matched_bank_ids out-sets to exclude from further passes.
     */
    std::vector<NativeBatchMatchResult> match_1toN_batch(
        const std::vector<NativeTransaction>& rzp_txns,
        const std::vector<NativeTransaction>& bank_txns,
        std::unordered_set<std::string>&      matched_rzp_ids,
        std::unordered_set<std::string>&      matched_bank_ids
    ) {
        std::vector<NativeBatchMatchResult> results;

        // Group unmatched RZP transactions by batch_id
        std::unordered_map<std::string, std::vector<size_t>> batch_groups;
        for (size_t i = 0; i < rzp_txns.size(); ++i) {
            const auto& r = rzp_txns[i];
            if (matched_rzp_ids.count(r.id) || r.batch_id.empty()) {
                continue;
            }
            batch_groups[r.batch_id].push_back(i);
        }

        // Precompute unmatched bank entries for fast scanning
        std::vector<size_t> avail_bank_idx;
        avail_bank_idx.reserve(bank_txns.size());
        for (size_t i = 0; i < bank_txns.size(); ++i) {
            if (!matched_bank_ids.count(bank_txns[i].id)) {
                avail_bank_idx.push_back(i);
            }
        }

        for (auto& [batch_id, rzp_indices] : batch_groups) {
            // Aggregate batch net paise sum and latest timestamp
            int64_t batch_sum = 0;
            int64_t latest_ts = 0;
            std::vector<std::string> rzp_ids_in_batch;

            for (size_t ri : rzp_indices) {
                batch_sum  += rzp_txns[ri].amount_net_paise;
                latest_ts   = std::max(latest_ts, rzp_txns[ri].timestamp_sec);
                rzp_ids_in_batch.push_back(rzp_txns[ri].id);
            }

            // Find a single bank credit entry matching the batch sum within time window
            for (size_t bi : avail_bank_idx) {
                const auto& bank = bank_txns[bi];
                if (matched_bank_ids.count(bank.id)) {
                    continue;
                }
                if (bank.amount_net_paise != batch_sum) {
                    continue;
                }
                int64_t t_delta = std::abs(bank.timestamp_sec - latest_ts);
                if (t_delta > time_window_sec_) {
                    continue;
                }

                // Found — record and mark used
                for (const auto& rid : rzp_ids_in_batch) {
                    matched_rzp_ids.insert(rid);
                }
                matched_bank_ids.insert(bank.id);

                results.push_back({
                    rzp_ids_in_batch,
                    bank.id,
                    batch_sum
                });
                break;
            }
        }

        return results;
    }

private:
    int64_t time_window_sec_;
};

// ---------------------------------------------------------------------------
// PyBind11 Module Definition
// ---------------------------------------------------------------------------

PYBIND11_MODULE(matcher_native, m) {
    m.doc() = "RECON-MESH Native C++ High-Throughput Heuristic Matcher (PyBind11)";

    py::class_<NativeTransaction>(m, "NativeTransaction")
        .def(py::init<std::string, std::string, int64_t, int64_t, std::string>(),
             py::arg("id"),
             py::arg("utr"),
             py::arg("amount_net_paise"),
             py::arg("timestamp_sec"),
             py::arg("batch_id") = "")
        .def_readwrite("id",               &NativeTransaction::id)
        .def_readwrite("utr",              &NativeTransaction::utr)
        .def_readwrite("amount_net_paise", &NativeTransaction::amount_net_paise)
        .def_readwrite("timestamp_sec",    &NativeTransaction::timestamp_sec)
        .def_readwrite("batch_id",         &NativeTransaction::batch_id);

    py::class_<NativeMatchResult>(m, "NativeMatchResult")
        .def_readonly("rzp_id",             &NativeMatchResult::rzp_id)
        .def_readonly("bank_id",            &NativeMatchResult::bank_id)
        .def_readonly("match_amount_paise", &NativeMatchResult::match_amount_paise)
        .def_readonly("time_delta_sec",     &NativeMatchResult::time_delta_sec);

    py::class_<NativeBatchMatchResult>(m, "NativeBatchMatchResult")
        .def_readonly("rzp_ids",            &NativeBatchMatchResult::rzp_ids)
        .def_readonly("bank_id",            &NativeBatchMatchResult::bank_id)
        .def_readonly("total_amount_paise", &NativeBatchMatchResult::total_amount_paise);

    py::class_<NativeHeuristicMatcher>(m, "NativeHeuristicMatcher")
        .def(py::init<int64_t>(), py::arg("time_window_sec") = 259200LL)
        .def("match_1to1",       &NativeHeuristicMatcher::match_1to1,
             py::arg("rzp_txns"), py::arg("bank_txns"))
        .def("match_1toN_batch", &NativeHeuristicMatcher::match_1toN_batch,
             py::arg("rzp_txns"), py::arg("bank_txns"),
             py::arg("matched_rzp_ids"), py::arg("matched_bank_ids"));
}

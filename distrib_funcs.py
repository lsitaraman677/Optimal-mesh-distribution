import sys
def no_split_distrib(binnum, vals):
    """
    Distribute a set of indivisible values across a fixed number of bins
    while controlling load imbalance via iterative exclusion and merging.
    Inputs
    ------
    binnum : int
        Number of bins (target level of parallelism).

    vals : sequence of numbers
        Per-item weights or costs. Each value is assigned whole to exactly
        one bin; values are not split.
    """
    # Sort values in descending order so larger items are placed first
    # (a greedy heuristic similar to largest-first bin packing)
    sortedvals = sorted(enumerate(vals), key=lambda x: x[1])[::-1]
    vals = [i[1] for i in sortedvals]
    idxs = [i[0] for i in sortedvals]
    # Initialize bins: res[i] will hold the values assigned to bin i
    res = [[] for _ in range(binnum)]

    # Target sum per bin (ideal perfectly balanced load)
    goal = sum(vals) / binnum

    # Remaining capacity to fill for each bin
    tofill = [goal for i in range(binnum)]

    # Seed each bin with one of the largest values (if possible)
    # This prevents early clustering of large values into one bin
    for i in range(min(binnum, len(vals))):
        res[i].append(idxs[i])
        tofill[i] -= vals[i]

    # Assign remaining values one by one
    for i in range(binnum, len(vals)):
        best = 0  # index of the bin chosen for the current value

        for j in range(1, binnum):
            # Perfect-fit shortcut: if value exactly fills remaining capacity
            #if tofill[j] == vals[i]:
            #    best = j
            #    break

            # Otherwise choose the bin with the most remaining capacity
            if tofill[j] > tofill[best]:
                best = j

        # Assign value to the selected bin
        res[best].append(idxs[i])
        tofill[best] -= vals[i]


    # Return the list of bins
    return res

def split_distrib(binnum, vals, tol=0.2):
    """
    Distribute a set of indivisible values across a fixed number of bins
    while controlling load imbalance via iterative exclusion and merging.

    Inputs
    ------
    binnum : int
        Number of bins (target level of parallelism).

    vals : sequence of numbers
        Per-item weights or costs. Each value is assigned whole to exactly
        one bin; values are not split.

    tol : float, optional
        Relative tolerance on bin overload. The allowed overload per bin is
        tol * (sum(vals) / binnum).

    Output
    ------
    combined : list of lists of int
        A list of length `binnum`. Each entry contains indices into `vals`
        assigned to that bin. Every index appears exactly once.

        The algorithm attempts to ensure that the total weight in each bin
        does not exceed the ideal per-bin load by more than the tolerance,
        subject to the heuristic nature of the method.

    Algorithm
    ---------

    Distribute values into bins with the option to *merge bins* if imbalance
    exceeds a tolerance.

    Unlike no_split_distrib, this allows post-processing that combines bins
    to reduce worst-case overload beyond a specified tolerance.

    Returns a list of (indices, group_size) pairs, where each group may
    represent one or more merged bins.
    """

    # Ideal target load per bin
    goal = sum(vals) / binnum

    # Absolute tolerance allowed for overload
    tol = tol * goal

    # Keep original indices so we can return assignments by index
    indexed_vals = [(i, vals[i]) for i in range(len(vals))]

    # Sort by value descending (largest-first heuristic)
    indexed_vals.sort(key=lambda x: x[1], reverse=True)

    # Separate indices and values after sorting
    idxs = [i for i, _ in indexed_vals]
    values = [v for _, v in indexed_vals]

    # Initial bin assignments (store indices, not values)
    bins = [[] for _ in range(binnum)]
    remaining = [goal for _ in range(binnum)]

    # --- Phase 1: Greedy distribution --------------------------------------
    # Seed each bin with one large value
    for i in range(min(binnum, len(values))):
        bins[i].append(idxs[i])
        remaining[i] -= values[i]

    # Assign remaining values to the bin with the most remaining capacity
    for i in range(binnum, len(values)):
        best = 0
        for j in range(1, binnum):
            # Perfect-fit shortcut
            if remaining[j] == values[i]:
                best = j
                break
            # Otherwise choose bin with most available space
            if remaining[j] > remaining[best]:
                best = j

        bins[best].append(idxs[i])
        remaining[best] -= values[i]

    # Track how many original bins are represented by each group
    group_sizes = [1 for _ in range(binnum)]

    # --- Phase 2: Bin merging to control overload ---------------------------
    # Iteratively merge the most underfilled and most overfilled bins
    while True:
        max_bin = None  # most remaining capacity
        min_bin = None  # most overloaded (most negative remaining)

        for i in range(binnum):
            if remaining[i] is None:
                continue
            if max_bin is None or remaining[i] > remaining[max_bin]:
                max_bin = i
            if min_bin is None or remaining[i] < remaining[min_bin]:
                min_bin = i

        # Stop if worst overload is within tolerance
        if (-remaining[min_bin]) <= tol:
            break

        # Merge min_bin into max_bin
        remaining[max_bin] += remaining[min_bin]
        bins[max_bin] += bins[min_bin]
        group_sizes[max_bin] += group_sizes[min_bin]

        # Mark min_bin as inactive
        remaining[min_bin] = None

    # --- Phase 3: Compact bins ----------------------------------------------
    # Remove inactive bins and shift results left
    shift = 0
    for i in range(binnum):
        if remaining[i] is None:
            shift += 1
        else:
            bins[i - shift] = (bins[i], group_sizes[i])

    # Remove trailing empty entries
    for i in range(binnum - 1, binnum - shift - 1, -1):
        bins.pop(i)

    distrib = [None for _ in range(binnum)]
    i = 0
    for b in bins:
        for _ in range(b[1]):
            distrib[i] = b[0]
            i += 1
    return distrib

def split_distrib2(binnum, vals, tol=0.2):

    """
    Distribute a set of indivisible values across a fixed number of bins
    while controlling load imbalance via iterative exclusion and merging.

    Inputs
    ------
    binnum : int
        Number of bins (target level of parallelism).

    vals : sequence of numbers
        Per-item weights or costs. Each value is assigned whole to exactly
        one bin; values are not split.

    tol : float, optional
        Relative tolerance on bin overload. The allowed overload per bin is
        tol * (sum(vals) / binnum).

    Output
    ------
    combined : list of lists of int
        A list of length `binnum`. Each entry contains indices into `vals`
        assigned to that bin. Every index appears exactly once.

        The algorithm attempts to ensure that the total weight in each bin
        does not exceed the ideal per-bin load by more than the tolerance,
        subject to the heuristic nature of the method.

    Algorithm
    ---------

    Iterative load-balancing with selective exclusion of large values.

    Items that cause overload beyond tolerance are temporarily ignored,
    the remaining items are rebalanced, and the ignored items are
    redistributed in a second pass. Final bin merging is applied if needed.
    """

    # Ideal target load
    goal = sum(vals) / binnum
    tol = tol * goal

    # Preserve original indices
    indexed_vals = [(i, vals[i]) for i in range(len(vals))]
    indexed_vals.sort(key=lambda x: x[1], reverse=True)

    idxs = [i for i, _ in indexed_vals]
    values = [v for _, v in indexed_vals]

    # Set of value indices temporarily removed from balancing
    ignore = set()

    # --- Phase 1: Iterative rebalance with exclusions -----------------------
    while True:
        # Compute effective goal excluding ignored items
        curgoal = sum(values[i] for i in range(len(values)) if i not in ignore)
        curgoal /= binnum

        # Fresh bins and remaining capacity
        res = [[] for _ in range(binnum)]
        tofill = [curgoal for _ in range(binnum)]

        # Seed bins with largest non-ignored values
        i = 0
        filled = 0
        while filled < binnum and i < len(values):
            if i in ignore:
                i += 1
                continue
            res[filled].append(i)
            tofill[filled] -= values[i]
            i += 1
            filled += 1

        # Greedy fill of remaining non-ignored values
        while i < len(values):
            if i in ignore:
                i += 1
                continue

            best = 0
            for j in range(1, binnum):
                if tofill[j] == values[i]:
                    best = j
                    break
                if tofill[j] > tofill[best]:
                    best = j

            res[best].append(i)
            tofill[best] -= values[i]
            i += 1

        # Identify worst-overloaded bins
        sorted_bins = sorted(
            [(k, tofill[k]) for k in range(binnum)],
            key=lambda x: x[1]
        )

        # Stop if overload is acceptable
        if (-sorted_bins[0][1]) <= tol:
            break

        # Otherwise, remove largest item(s) from overloaded bins
        idx = 0
        if (-sorted_bins[idx][1]) > tol:
            bin_id = sorted_bins[idx][0]
            bin_items = res[bin_id]

            # Find largest value in this bin
            max_item = max(bin_items, key=lambda x: values[x])

            # Exclude it from future passes
            ignore.add(max_item)
            idx += 1

    # Convert working indices back to original indices
    for b in res:
        for j in range(len(b)):
            b[j] = idxs[b[j]]

    # --- Phase 2: Redistribute ignored values --------------------------------
    cutvals = [(idxs[i], values[i]) for i in ignore]
    cutvals.sort(key=lambda x: x[1], reverse=True)

    cutidxs = [i for i, _ in cutvals]
    cutvalues = [v for _, v in cutvals]

    cutgoal = sum(cutvalues) / binnum

    # Reinflate bin capacities to accept ignored values
    for i in range(binnum):
        tofill[i] += cutgoal

    cutres = [[] for _ in range(binnum)]

    # Greedy assignment of ignored values
    for i in range(len(cutvalues)):
        best = 0
        for j in range(1, binnum):
            if tofill[j] == cutvalues[i]:
                best = j
                break
            if tofill[j] > tofill[best]:
                best = j

        cutres[best].append(cutidxs[i])
        tofill[best] -= cutvalues[i]

    # --- Phase 3: Final bin merging ------------------------------------------
    groupidxs = [[i] for i in range(binnum)]

    while True:
        ma = None
        mi = None
        for i in range(binnum):
            if tofill[i] is None:
                continue
            if ma is None or tofill[i] > tofill[ma]:
                ma = i
            if mi is None or tofill[i] < tofill[mi]:
                mi = i

        if (-tofill[mi]) <= tol:
            break

        # Merge most overloaded with most underfilled
        tofill[ma] += tofill[mi]
        tofill[mi] = None

        merged = cutres[ma] + cutres[mi]
        merged_idxs = groupidxs[ma] + groupidxs[mi]

        for idx in merged_idxs:
            cutres[idx] = merged
            groupidxs[idx] = merged_idxs

    # --- Phase 4: Combine main + ignored assignments -------------------------
    combined = []
    for i in range(binnum):
        combined.append(res[i] + cutres[i])

    # Reorder to ensure groups are in adjacent ranks to make communication more efficient
    new_idxs = [None for _ in range(binnum)]
    used = set()
    cur = 0
    singles = []
    for j in range(binnum):
        group = groupidxs[j]
        if len(group) == 1:
            singles.append(j)
            continue
        elif group[0] in used:
            continue
        used.add(group[0])
        for i in group:
            new_idxs[cur] = i
            cur += 1
    for i in singles:
        new_idxs[cur] = i
        cur += 1
    reordered = [None for _ in range(binnum)]
    for i in range(binnum):
        reordered[i] = combined[new_idxs[i]]

    return reordered

def over_cut(binnum, vals):
    vals_list = list(range(len(vals)))
    return [vals_list for _ in range(binnum)]


if __name__ == '__main__':

    bins = int(sys.argv[1])
    sizes = [float(i) for i in sys.argv[2:]]


    n = 3
    funcs = [no_split_distrib, split_distrib, split_distrib2]
    res = funcs[n-1](bins, sizes)

    print('result: ')
    print(res)

    if n > 1:
        vals = []
        fullcomb = []
        for i in res:
            fullcomb += i
        for i in res:
            cur = []
            for j in (i[0] if (n == 2) else i):
                cur.append(sizes[j] / (i[1] if (n == 2) else fullcomb.count(j)))
            for _ in range(i[1] if (n == 2) else 1):
                vals.append(cur)
        print('values: ')
        print(vals)
        print('sums: ')
        print([sum(i) for i in vals])
        print('expected mean: ')
        print(sum(sizes) / bins)
        print('worst rank: ')
        print(max([sum(i) for i in vals]))

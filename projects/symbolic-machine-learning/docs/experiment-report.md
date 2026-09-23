# Decision-Tree Improvement Experiment

[English](experiment-report.md) | [한국어](experiment-report.ko.md) | [Project README](../README.md)

## Executive summary

This experiment compared the baseline decision-tree learner (`dtl`) with `my-dtl`, a variant that uses gain ratio and a tree-growth control heuristic. The historical coursework results show a clear speed improvement and better accuracy in one high-noise configuration, but weaker performance in several lower-noise and limited-data configurations.

The results are preserved as recorded evidence. They were not rerun during the portfolio reorganisation.

## Research question

Can normalised attribute selection and restricted tree growth reduce overfitting to noisy data while lowering training time?

## Changes evaluated

### Gain ratio

The baseline selects attributes using information gain:

```text
Gain(S, A) = Entropy(S) - Σᵥ |Sᵥ| / |S| × Entropy(Sᵥ)
```

`my-dtl` divides that value by the entropy of the split:

```text
SplitInfo(S, A) = -Σᵥ |Sᵥ| / |S| × log₂(|Sᵥ| / |S|)
GainRatio(S, A) = Gain(S, A) / SplitInfo(S, A)
```

This penalises attributes whose many values fragment the dataset into small partitions.

### Tree-growth control

The implementation sets a maximum-depth target to `floor(log2(n))`, where `n` is the number of training examples, and returns a plurality leaf after the limit is reached.

There is an important implementation caveat: the current code stores depth in one shared counter and increments it after child subtrees are built. It is therefore a global post-order growth heuristic rather than a precise root-to-leaf depth calculation. The recorded results describe the submitted implementation, not an idealised per-branch depth limiter.

## Reproduction commands

Run these commands from `projects/symbolic-machine-learning` after installing the dependencies.

```bash
python evaluate_attributes.py eval-time -a dtl -a my-dtl -s 5 -s 7 -s 10
python evaluate_attributes.py eval-noisy -a dtl -a my-dtl -c 0.3 -c 0.5 -c 0.7 -s 10 -d 5
python evaluate_attributes.py eval-noisy -a dtl -a my-dtl -c 0.3 -c 0.5 -c 0.7 -s 10 -d 10
python evaluate_attributes.py eval-size -a dtl -a my-dtl -t 0.3 -t 0.5 -t 0.7 -s 10 -d 5
python evaluate_attributes.py eval-size -a dtl -a my-dtl -t 0.3 -t 0.5 -t 0.7 -s 10 -d 10
```

The scripts use a deterministic default seed (`42`), but runtime still depends on the machine and software environment.

## Recorded results

### Training time

| Examples | Attributes | `dtl` | `my-dtl` | Recorded reduction |
| ---: | ---: | ---: | ---: | ---: |
| 32 | 5 | 0.271 ± 0.004 ms | 0.151 ± 0.002 ms | 44% |
| 128 | 7 | 1.335 ± 0.011 ms | 0.415 ± 0.003 ms | 69% |
| 1,024 | 10 | 14.946 ± 0.134 ms | 3.033 ± 0.021 ms | 80% |

The speed advantage grew with the dataset size in these measurements.

### Accuracy with noisy labels

Ten attributes, with ten relevant attributes:

| Corrupted labels | `dtl` | `my-dtl` | Difference |
| ---: | ---: | ---: | ---: |
| 30% | 69.9% | 51.3% | -18.6 pp |
| 50% | 50.0% | 50.1% | +0.1 pp |
| 70% | 30.0% | 49.1% | +19.1 pp |

Ten attributes, with five relevant attributes:

| Corrupted labels | `dtl` | `my-dtl` | Difference |
| ---: | ---: | ---: | ---: |
| 30% | 69.9% | 77.5% | +7.6 pp |
| 50% | 50.0% | 51.8% | +1.8 pp |
| 70% | 30.0% | 32.3% | +2.3 pp |

The strongest gain appears in the extreme-noise, ten-relevant-attribute case. The same model loses substantially at 30% noise in that configuration, so the experiment does not support a general accuracy improvement.

### Accuracy with less training data

Five relevant attributes:

| Training examples | `dtl` | `my-dtl` | Difference |
| ---: | ---: | ---: | ---: |
| 308 | 100.0% | 84.4% | -15.6 pp |
| 512 | 95.7% | 86.1% | -9.6 pp |
| 717 | 98.0% | 69.4% | -28.6 pp |

Ten relevant attributes:

| Training examples | `dtl` | `my-dtl` | Difference |
| ---: | ---: | ---: | ---: |
| 308 | 51.3% | 50.3% | -1.0 pp |
| 512 | 49.4% | 50.2% | +0.8 pp |
| 717 | 53.7% | 54.1% | +0.4 pp |

The five-attribute results expose a large loss from restricting model growth. With ten relevant attributes, both algorithms remain close to chance under the recorded setup.

## Interpretation

- **Confirmed:** `my-dtl` was consistently faster in the recorded timing experiment.
- **Partially supported:** it resisted one extreme-noise configuration much better than `dtl`.
- **Rejected as a general claim:** it did not improve accuracy across noise levels or limited-data settings.
- **Engineering lesson:** regularisation strength should be selected from validation data rather than derived from training-set size alone.

## Threats to validity

- Results come from pseudo-random synthetic Boolean datasets rather than external benchmark datasets.
- The noise evaluation restores labels and evaluates on the full generated dataset, so training and evaluation data overlap.
- A single default random seed limits confidence in variability across generated hypotheses.
- Runtime values are environment-specific.
- The shared depth counter does not represent true branch depth.
- Statistical output from the evaluation tool is not reproduced in this report, so percentage differences should not be read as proof of significance.

## Next steps

1. Pass branch depth as a recursive argument instead of keeping shared mutable state.
2. Select maximum depth using a validation split or post-pruning.
3. Repeat every configuration across multiple seeds and report confidence intervals.
4. Evaluate on external categorical datasets in addition to synthetic data.
5. Compare gain ratio alone, depth control alone, and the combined method through an ablation study.

# Exercise 3: Decision Tree Learner Improvements

## Introduction
The baseline Decision Tree Learner (DTL) algorithm exhibited vulnerability to noisy data. For instance, with 30% noise in the dataset, DTL achieved an accuracy of 70%, which dropped to 50.0% at 50% noise and further to 30.0% at 70% noise, suggesting potential overfitting. To mitigate this issue, the `my-dtl` algorithm was developed with the goal of enhancing robustness to noise and reducing training time. This was achieved by modifying the information gain calculation to use Gain Ratio and restricting the tree depth, thereby improving the algorithm's efficiency and resilience to noisy data.

## Improvements Implemented
1. Maximum Depth Restriction

**What:** Restricted the maximum tree depth to int(log2(n)), where n is the number of training examples.

**Why:** To prevent overfitting in noisy datasets by creating shallower trees and to reduce computational complexity, thereby decreasing training time.

**Hypothesis:** Limiting tree depth will significantly reduce training time across all dataset sizes and improve accuracy in high-noise datasets by mitigating overfitting.

**Implementation:**
    def find_hypothesis(self):
        n = len(self.dataset.examples)
        self.max_depth = int(log2(n)) if n > 0 else 1
        self.depth = 0
        ...

    def decision_tree_learning(self, examples: Examples, attributes: List[str], parent_examples: Examples) -> Tree:
        ...
        if not attributes or self.depth >= self.max_depth:
            return Leaf(target=plurality_value(examples))
        ...

2. Gain Ratio for Attribute Selection

**What:** Replaced Information Gain with Gain Ratio (info_gain / split_info) as the criterion for selecting the most informative attribute.

**Why:** The baseline DTL algorithm uses Information Gain, which is biased towards attributes with many values, as these attributes tend to create smaller, more homogeneous subsets, resulting in artificially high gains. In datasets with noisy attributes, this bias can lead to poor attribute selection, exacerbating overfitting in high-noise conditions. Gain Ratio mitigates this by normalizing Information Gain with Split Information, which penalizes attributes with many values, ensuring more robust attribute selection in noisy environments.

**Theoretical Background:** Information Gain measures the reduction in entropy after splitting a dataset based on an attribute, defined as:
Gain(S, A) = Entropy(S) - Σ(|S_v|/|S| * Entropy(S_v))
where S is the dataset, A is the attribute, S_v is the subset for value v of A, and Entropy(S) = -Σ(p_i * log2(p_i)) for class probabilities p_i. However, attributes with many values (e.g., 10 possible values) often produce small subsets with low entropy, inflating the gain. Gain Ratio addresses this by dividing Information Gain by Split Information:
SplitInfo(S, A) = -Σ(|S_v|/|S| * log2(|S_v|/|S|))
GainRatio(S, A) = Gain(S, A) / SplitInfo(S, A)
Split Information measures the entropy of the attribute’s value distribution, penalizing attributes that split the dataset into many small subsets. This normalization makes Gain Ratio particularly effective in datasets with noisy or irrelevant attributes, as it prioritizes attributes that provide meaningful class discrimination.

**Hypothesis:** By using Gain Ratio, `my-dtl` will improve attribute selection in high-noise datasets, leading to higher accuracy compared to DTL, which suffers from overfitting due to biased attribute selection.

**Implementation:**
    def information_gain(self, examples: Examples, attribute: str) -> float:
        total_entropy = binary_entropy(examples)
        value_groups = {}
        for ex in examples:
            val = ex[attribute]
            value_groups.setdefault(val, []).append(ex)

        weighted_entropy = 0.0
        split_info = 0.0
        total_size = len(examples)
        for group in value_groups.values():
            group_size = len(group)
            weight = group_size / total_size
            weighted_entropy += weight * binary_entropy(group)
            split_info -= weight * log2(weight) if weight > 0 else 0

        if split_info == 0:
            return 0
        info_gain = total_entropy - weighted_entropy
        return info_gain / split_info

## Experimental Setup
To evaluate the performance of `my-dtl` against the baseline Decision Tree Learner (DTL), a series of experiments were conducted across three key metrics: training time, accuracy with noisy data, and accuracy with less training datasets. The experimental setup is designed to assess the effectiveness of the implemented improvements, particularly the use of Gain Ratio for attribute selection and maximum depth restriction.

**Metrics:**
    Training Time: Measured in milliseconds (ms), reported as the average ± standard deviation over multiple runs to account for computational variability.

    Accuracy: Measured as the percentage (%) of correctly classified test examples, with statistical significance assessed at p=0.05 to determine whether differences between My-DTL and DTL are meaningful.

**Baseline:** The original DTL algorithm, which uses Information Gain for attribute selection and does not impose depth restrictions or optimized grouping, served as the baseline for comparison.

**Commands:** The following commands were executed to perform the evaluations:
```bash
python evaluate_attributes.py eval-time -a dtl -a my-dtl -s 5 -s 7 -s 10
python evaluate_attributes.py eval-noisy -a dtl -a my-dtl -c 0.3 -c 0.5 -c 0.7 -s 10 -d 5
python evaluate_attributes.py eval-noisy -a dtl -a my-dtl -c 0.3 -c 0.5 -c 0.7 -s 10 -d 10
python evaluate_attributes.py eval-size -a dtl -a my-dtl -t 0.3 -t 0.5 -t 0.7 -s 10 -d 5
python evaluate_attributes.py eval-size -a dtl -a my-dtl -t 0.3 -t 0.5 -t 0.7 -s 10 -d 10
```

## Results and Analysis
The performance of `my-dtl`was evaluated against the baseline Decision Tree Learner (DTL) across three metrics: training time, accuracy with noisy data, and accuracy with less training datasets. 

**Training Time**
Results:
    n=32, attributes=5: My-DTL 0.151ms ± 0.002ms vs. DTL 0.271ms ± 0.004ms (44% faster).
    n=128, attributes=7: My-DTL 0.415ms ± 0.003ms vs. DTL 1.335ms ± 0.011ms (69% faster).
    n=1024, attributes=10: My-DTL 3.033ms ± 0.021ms vs. DTL 14.946ms ± 0.134ms (80% faster).

Analysis: The hypothesis that maximum depth restriction would significantly reduce training time is confirmed. My-DTL consistently outperformed DTL by 44~80%, with the largest dataset (n=1024, 10 attributes) showing an impressive 80% reduction. 

**Noisy Data Accuracy**
Results (10 attributes, n=1024):
    Noise 0.3: My-DTL 51.3% vs. DTL 69.9% (18.6% worse).
    Noise 0.5: My-DTL 50.1% vs. DTL 50.0% (0.1% better).
    Noise 0.7: My-DTL 49.1% vs. DTL 30.0% (19.1% better).

Results (5 attributes, n=1024):
    Noise 0.3: My-DTL 77.5% vs. DTL 69.9% (7.6% better).
    Noise 0.5: My-DTL 51.8% vs. DTL 50.0% (1.8% better).
    Noise 0.7: My-DTL 32.3% vs. DTL 30.0% (2.3% better).

Analysis: The hypothesis that Gain Ratio would improve accuracy in high-noise datasets is partially confirmed. For 10 attributes at noise=0.7, My-DTL achieved a significant 19.1% improvement (49.1% vs. 30.0%), demonstrating robustness where DTL’s accuracy fell below random guessing (50%). This is attributed to Gain Ratio’s ability to mitigate bias towards attributes with many values, prioritising informative attributes despite the presence of 5 irrelevant attributes. The depth restriction further reduced overfitting, contributing to this success. However, at low noise (0.3, 10 attributes), My-DTL underperformed (51.3% vs. 69.9%), likely because Gain Ratio alone could not fully filter out noisy attributes in less noisy conditions. For 5 attributes, My-DTL outperformed DTL at noise=0.3 (77.5% vs. 69.9%), but gains diminished at higher noise levels, suggesting that depth restrictions oversimplified the tree in extreme noise scenarios.

**Less Data Accuracy**
Results (5 attributes, n=1024):
    Training 308: My-DTL 84.4% vs. DTL 100.0% (15.6% worse).
    Training 512: My-DTL 86.1% vs. DTL 95.7% (9.6% worse).
    Training 717: My-DTL 69.4% vs. DTL 98.0% (28.6% worse).

Results (10 attributes, n=1024):
    Training 308: My-DTL 50.3% vs. DTL 51.3% (1.0% worse).
    Training 512: My-DTL 50.2% vs. DTL 49.4% (0.8% better).
    Training 717: My-DTL 54.1% vs. DTL 53.7% (0.4% better).

Analysis: For 5 attributes, My-DTL significantly underperformed DTL, with accuracy gaps of 9.6~28.6%. The restrictive depth (int(log2(n))) resulted in overly simple trees that failed to capture complex patterns in small datasets. For 10 attributes, both algorithms performed similarly, hovering around 50%, indicating that neither algorithm could effectively learn from limited data. This suggests that the current improvements are not suited for small datasets, where deeper trees or additional mechanisms are needed.

**Summary**
The results demonstrate that `my-dtl` excels in training time (44~80% faster) and high-noise accuracy (19.1% better at noise=0.7, 10 attributes), driven by maximum depth restriction,and Gain Ratio. However, it struggles in low-noise (noise=0.3, 10 attributes) and small dataset scenarios due to noisy attribute interference and oversimplified trees. These findings validate the effectiveness of Gain Ratio in high-noise conditions but highlight the need for further enhancements to address low-noise and small dataset limitations.

## Discussion
The evaluation of `my-dtl` against the baseline Decision Tree Learner (DTL) reveals significant successes in training time and high-noise data accuracy, alongside notable limitations in low-noise and less dataset scenarios. This section synthesises the results, analysing the effectiveness of the implemented improvements, maximum depth restriction, and Gain Ratio for attribute selection and drawing key lessons for future development.

**Successes:**
Training Time: `my-dtl` achieved an impressive 44~80% reduction in training time across dataset sizes, with the most substantial improvement of 80% for the largest dataset (n=1024, 10 attributes: 3.033ms vs. 14.946ms). This success is driven by the maximum depth restriction (int(log2(n))), which limited tree growth and reduced recursive computations. These improvements make My-DTL highly efficient, particularly for large-scale datasets, addressing a critical limitation of DTL’s computational complexity.

High-Noise Accuracy: In high-noise conditions (noise=0.7, 10 attributes), My-DTL outperformed DTL by 19.1% (49.1% vs. 30.0%), achieving near-random guessing accuracy (50%) where DTL failed significantly. This robustness is primarily attributed to the use of Gain Ratio. The depth restriction further contributed by preventing overfitting, ensuring that the tree did not capture noise-induced patterns. This result validates the hypothesis that Gain Ratio and depth limits enhance performance in noisy environments.

**Failures:**
Low-Noise Accuracy: At low noise levels (noise=0.3, 10 attributes), My-DTL underperformed DTL by 18.6% (51.3% vs. 69.9%). While Gain Ratio reduces bias compared to Information Gain, it still selected suboptimal attributes when noise was moderate, leading to less accurate trees. Additionally, the depth restriction may have oversimplified the tree, limiting its ability to capture true patterns in low-noise data.

Less Datasets: For less training datasets with 5 attributes (n=308, 512, 717), My-DTL exhibited significant accuracy gaps of 9.6~28.6% compared to DTL (e.g., n=308: 84.4% vs. 100.0%). The restrictive depth (int(log2(n))) resulted in overly simple trees that failed to learn complex patterns necessary for small datasets. For 10 attributes, both algorithms performed poorly (50% accuracy). This indicates that the current improvements, particularly the depth restriction, are not well-suited for scenarios with limited training data, where deeper trees or additional mechanisms are required.

**Lessons Learnt:**
Gain Ratio’s Robustness: Gain Ratio significantly enhances high-noise robustness by prioritising informative attributes, as evidenced by the 19.1% improvement at noise=0.7. However, its effectiveness diminishes in low-noise conditions with noisy attributes, suggesting the need for complementary attribute filtering mechanisms.

Depth Restriction Trade-offs: Limiting tree depth is highly effective for training time (80% reduction) and high-noise accuracy but compromises performance in low-noise and small datasets by oversimplifying the model. A more adaptive depth strategy could balance these trade-offs.

Noisy Attributes Challenge: The presence of irrelevant attributes of significantly impacts performance, particularly in low-noise and small dataset scenarios, highlighting the need for attribute selection or sampling techniques to mitigate their influence.

The successes in training time and high-noise accuracy demonstrate the value of the implemented improvements, particularly Gain Ratio and depth restriction, in addressing DTL’s vulnerabilities to noise and computational inefficiency. However, the failures in low-noise and small dataset scenarios underscore the limitations of the current approach, providing clear directions for future enhancements to achieve broader performance improvements.

## Conclusion
`my-dtl` exhibits limitations in low-noise and less dataset scenarios. In low-noise conditions (noise=0.3, 10 attributes), it achieves only 51.3% accuracy compared to DTL’s 69.9%, likely due to the interference of noisy attributes. Similarly, with small training datasets (5 attributes, n=308), its accuracy of 84.4% lags behind DTL’s 100.0%, as the restrictive depth limit oversimplifies the tree, hindering pattern capture.

Techniques such as post-pruning or attribute sampling could address these shortcomings, potentially improving accuracy in low-noise and small dataset scenarios by reducing overfitting and mitigating the impact of irrelevant attributes. By exploring these approaches, `my-dtl` could evolve into a more robust and generalisable algorithm, capable of handling a wider range of datasets effectively.

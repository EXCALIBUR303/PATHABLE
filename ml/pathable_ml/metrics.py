"""Classification metrics with counts and explicit empty-denominator nulls."""


def classification(classes, expected, predicted):
    if not expected or len(expected) != len(predicted):
        raise ValueError("Nonempty aligned observations required")
    matrix = [[0 for _ in classes] for _ in classes]
    for target, actual in zip(expected, predicted, strict=True):
        matrix[classes.index(target)][classes.index(actual)] += 1
    per_class = []
    for i, label in enumerate(classes):
        tp = matrix[i][i]
        support = sum(matrix[i])
        selected = sum(row[i] for row in matrix)
        precision = tp / selected if selected else None
        recall = tp / support if support else None
        denominator = support + selected
        per_class.append(
            {
                "class_name": label,
                "support": support,
                "precision": precision,
                "recall": recall,
                "f1": 2 * tp / denominator if denominator else None,
            }
        )
    return {
        "sample_count": len(expected),
        "confusion_matrix": matrix,
        "per_class": per_class,
        "accuracy": sum(matrix[i][i] for i in range(len(classes))) / len(expected),
    }

# Interpretation Rules

## File Naming

Each image file is named after the disease it represents (e.g., `1.肩峰下滑囊炎.png`).

## 9x9 Grid

The grid represents the range of motion around the shoulder joint.

- **Center**: Center of the shoulder
- **Grid cells**: Each cell corresponds to a spot where the arm hurts when it moves in a circular direction from the center

## Dot Colors (Severity)

- **Red**: Serious (嚴重)
- **Yellow**: Mild (中度)
- **Blue**: Light (輕微)
- **Black**: Exclusion zone - in clinical practice, doctors visually exclude the disease if hurt occurs in that area. Ignored in this system because the input app does not capture this information.

## Alphabet Characters

The letter inside each colored dot (e.g., C, W) indicates the type of hurt. Ignored in the current system.

## Diagnosis Logic

A disease is identified by how many hurt points match the pattern and their severity degree. The disease with the highest weighted score is the primary diagnosis.

# Grading Agent

**Backend**: `agents/grading_agent.py` + `agents/graders/visual_grading_agent.py`

## Purpose
AI-powered Pokemon card grading evaluating centering, corners, edges, and surface condition with predicted PSA/CGC/BGS grades from front/back photos.

## API Endpoints
- `POST /grading/evaluate` - Predict grade from card images
- `POST /grading/batch` - Grade multiple cards
- `GET /grading/standards` - Return official grading criteria

## Inputs / Outputs
**Input**: Card image(s) (base64 or URL), card details
**Output**: Predicted PSA/CGC/BGS grades, confidence scores, condition breakdown

## Key Dependencies
- `graders/visual_grading_agent.py` - Vision-based grading analysis
- `graders/grading_standards.py` - Official grading criteria
- `market/graded_prices.py` - Expected value lookup

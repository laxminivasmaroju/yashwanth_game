# DATA SIEGE — Stage 1 playable prototype

A top-down, two-lane real-time tower-defence prototype built with Python and Pygame. The game uses original drawn shapes and names rather than copied Clash Royale assets.

## Run

1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Install dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Start the game:

   ```bash
   python main.py
   ```

Pygame is the only dependency used by this first prototype. The other libraries are included for the upcoming Machine Learning laboratory.

## Controls

- Click a troop card, then click the lower half of the arena near either bridge to deploy.
- Keys `1`, `2`, `3` select Guardian, Ranger and Titan.
- `ESC` cancels the selected card.
- `R` restarts after victory or defeat.

## Stage 1 features

- Two lanes and bridges
- Three player towers and three enemy towers
- Three troop cards with different costs, health, damage, range and speed
- Regenerating elixir
- Basic enemy deployment AI
- Automatic tower defence
- Victory/defeat conditions
- JSON save on victory (`data/progress.json`)

## Development roadmap

- Stage 2: improve enemy tactics, troop targeting, projectile effects, deck selection and battle balancing.
- Stage 3: Campaign 1 lessons and real classification workflow (data collection, preprocessing, features/labels, train/test split).
- Stage 4: Campaign 2 with decision trees, KNN, K-means, scaling and decision boundaries.
- Stage 5: Campaign 3 with regression, confusion matrix, accuracy, precision, recall and overfitting/underfitting.
- Stage 6: ML lab UI, progression, boss battles, audio, settings and polish.

## Notes

This is an initial playable prototype, not the finished game. The current troop and enemy behaviour is intentionally simple so the core battle loop can be tested before adding more complex systems and ML mechanics.

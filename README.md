# Space Control
## How to run
```
pip install -r requirements.txt            # pygame-ce + pytest
pip install -r requirements-gesture.txt    # tensorflow, tf-keras, opencv, numpy (needed to play)

python -m src.main                         # the game (gesture control, settings in config.toml)
```
## Overview
the idea is that we make a retro style game Similar to old spaceship 8-bit games like space invaders and galaga. A Game where you control a spaceship and navigate through space, shooting & avoiding enemies. but with a twist. it is controlled using hand gestures that are trained in Google Teachable Machine, and it returns "L" and "R", the game uses computer vision to detect the hand gestures and processes it through the Techable machine api to make the character go left and right. The goal is to survive 5 waves.

Currently the game shows a lot of enemies and thats it, we want that to change, each wave should have a different distribution of enemies, and the enemies should have different behaviors, some should shoot, some should move in a zig-zag pattern, some should move in a straight line, some should move in a circular pattern, etc. The game should also have a scoring system, and the player should be able to see their score at the end of the game.

By the end of the Five waves the game ends and the user is prompted to enter his/her name and add it to the leaderboard.

The Game Ui should be updated to the one seen in ./ui-new

The Game shouldnt work with keyboard, only hand gesture control, the main page should show me the status of connecting to Google Teachable Machine, and the game should only start when the connection is established.

Techable machine return "L", "R" and "N" for left, right and neutral respectively, the game should be able to process these inputs and move the character accordingly.

The teachable machine link should be configurable in a config file, and the game should be able to connect to it and process the inputs accordingly.

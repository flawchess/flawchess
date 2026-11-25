# The Facepalm Score, Explained

**Audience:** an advanced chess player with some technical curiosity. It assumes you know chess well but not statistics or machine learning. The few technical ideas (a human-move model, a weighted formula, a ranking that is not a probability) are explained from scratch.

**Purpose:** a durable, plain-language explanation of *what the Facepalm Score measures, how it is computed, and where FlawChess uses it.*

---

## 1. What problem the score solves

An engine calls a move a blunder when it costs a lot. In FlawChess that means the move dropped your Expected Score (your winning chances, read off the Stockfish evaluation) by at least 15 percentage points. That definition says how *expensive* the move was. It says nothing about how *avoidable* it was.

Those are very different things. Two blunders can cost exactly the same and feel nothing alike:

- **You leave a rook on a square where a pawn takes it.** You see it the moment you let go of the piece. That is a facepalm.
- **You play a natural developing move that loses to a quiet seven-move engine line.** Nobody at your level would have found the refutation, including your opponent. Calling this a "blunder" is technically right and practically useless.

A blunder list that mixes both kinds buries the lessons you can act on under the ones you cannot. The Facepalm Score separates them. It answers one question:

> **How easy should this blunder have been to see, for a player at your level?**

The answer is a number from 0% to 100%. Low means "probably hard to see, don't beat yourself up." High means "you should have caught this." A blunder that scores **70% or more** is a **facepalm blunder** and gets the `???` mark instead of the usual `??`.

---

## 2. The ingredients

The score does not look at the position with any chess understanding of its own. It combines three kinds of facts that FlawChess already has about each blunder.

**The engine lines (Stockfish).** For every blunder there are two lines: the line that punishes the move you played, and the line that starts with the best move you could have played instead. These tell us *what actually happens* on the board.

**The human-move model (Maia).** Maia is a neural network trained on millions of human games. Give it a position and a rating, and it returns how likely a player of that rating is to play each legal move. It is the opposite of Stockfish: it predicts what people do, not what is best. The score asks Maia three questions, always at the rating of the player who blundered:

1. How likely was the move you actually played?
2. How likely was the best move?
3. After your blunder, how likely is the opponent's punishing reply?

**A simple material count.** Along both engine lines FlawChess counts material with the classic values (pawn 1, knight and bishop 3, rook 5, queen 9). This gives two numbers, described in the next section: how much material your move **loses**, and how much material the best move would have **won** that you left on the table.

"At your level" is literal. Your rating in that game is converted to a common scale (lichess blitz equivalent, limited to the 600 to 2600 range Maia covers) and Maia is asked about a player of exactly that strength. The same blunder can be a facepalm for an 1800 and a forgivable miss for a 1000.

---

## 3. Counting material the way a player would

Counting material along an engine line sounds trivial and is full of traps. Engines trade pieces in long sequences, throw in spite checks when lost, and "win" material ten moves deep that no human was ever going to see. The count follows a few rules so that it matches how a player reads the line.

**Wait until the dust settles.** The count is never taken in the middle of an exchange. If the line goes queen takes queen, rook takes queen, the count is read after the recapture, so an even trade is worth zero rather than "you lost a queen."

**Look a few moves deep, but trust the near future most.** The count is read at five points along the line: after 1, 3, 5, 7 and 9 half-moves. These are averaged with weights that halve each step (1, ½, ¼, ⅛, 1⁄16). A piece that drops immediately and stays lost counts as a full 3 points. A piece that only falls five half-moves into the line counts as about 0.7. This is the built-in idea that material lost *right now* is far more visible than material lost at the end of a long forced sequence.

**Cap the size.** Losses and missed gains are capped at 5 points. Hanging a queen is not meaningfully more of a facepalm than hanging a rook: both are as obvious as it gets. A quick checkmate also counts as 5, whether you walked into it or failed to deliver it.

**Promotions are material.** Letting a pawn queen, or missing your own promotion, counts like losing or missing that piece.

**Ignore engine desperation.** In a lost position an engine often gives away a piece for nothing just to delay the inevitable. Material thrown away like that in the line is not counted as part of what the blunder cost.

The two results are:

- **Loss:** how much material you are down along the punishing line, compared to the position before your move.
- **Missed:** how much more material the best line would have won, compared to what your move got you.

---

## 4. Two types of blunder: allowed loss and missed win

Every scored blunder is one of two types, decided purely by the two material numbers:

- **Allowed loss:** your move gave away material or allowed checkmate. (The loss is above zero and at least as large as what you missed.)
- **Missed win:** the best move won material or led to checkmate, and you did not play it. (Everything else, including blunders where no material changes hands in either line.)

The type matters because the two fail for different reasons, and the score judges each on the move that matters for it:

- For an **allowed loss**, the key question is *how obvious is the punishment?* The score looks at how likely your opponent's punishing reply is. If nearly everyone at your level would find the capture, you should have seen it coming.
- For a **missed win**, the key question is *how obvious was the winning move?* The score looks at how likely the best move was. If most players at your level play it, missing it is on you.

---

## 5. Putting it together

The score is a weighted sum of the ingredients, squeezed into the 0% to 100% range. In words, a blunder scores **higher** when:

- **it loses more material** (the strongest single factor);
- **it misses more material** (counts, but less than half as much as losing the same amount: giving something away is more glaring than failing to take something);
- **the key move is likely for a player at your level** (the punishing reply for an allowed loss, the best move for a missed win);
- **the move you played is unusual for your level.** If a large share of your peers would play the same move, it is a typical trap for your rating and the score goes down. If almost nobody would, you went out of your way to find it.

Some illustrative cases, computed with the current model:

| Blunder | Facepalm score |
|---|---|
| Hang a rook (or more) with an unusual move; the capture is obvious (90% likely) | 98% |
| Hang a piece with a natural-looking move; the capture is obvious (90%) | 79% |
| Same piece, same move, but the refutation is hard to find (5%) | 30% |
| Lose a pawn to an obvious reply (80%) | 41% |
| Miss a quick mate or a rook; the winning move was obvious (70%) | 76% |
| Miss winning a piece; the winning move was obvious (70%) | 59% |
| Miss winning a piece; the winning move was very hard to find (3%) | 3% |
| No material at stake in either line; the best move was a coin flip (50%) | 14% |

A few things worth noticing. Dropping a single pawn rarely reaches the 70% line, however obvious. A missed win has to be both large and obvious to qualify. And a purely positional blunder (no material in sight) almost never counts as a facepalm, which matches the feeling: you do not slap your forehead over a subtly worse pawn structure.

---

## 6. Where the weights come from

The weights were not chosen by hand and not learned from game results. They were fitted to human judgment.

The site owner went through several hundred of his own blunders one by one and labeled each as **fair** ("yes, I should have seen that") or **unfair** ("no reasonable chance at my level"). A handful were marked undecided and left out. The 268 clear cases, split almost evenly between the two labels, are the training set. A standard statistical method (logistic regression) then found the weights that best separate fair from unfair.

The *shape* of the formula (which ingredients, which key move for which type) was fixed in advance from chess reasoning. Only the weights were fitted. This was deliberate: with a few hundred labels, letting the data choose the shape as well would mostly fit noise.

How well does it work? If you pick one fair and one unfair blunder at random, the score ranks the fair one higher about 89% of the time on blunders it was not trained on. Among labeled blunders scoring 70% or more, roughly nine in ten were labeled fair.

---

## 7. What the score is not

**It is not a probability.** A score of 80% does not mean "80% of players at your level would have avoided this," and FlawChess never words it that way. The labels are a ranking exercise on one player's blunders, so the score is a ranking: higher means more avoidable, and 70% is the line the labels were drawn around. Read it like a difficulty rating, not a statistic about your peers.

**It is not a second opinion on whether the move was bad.** Every scored move is already a blunder by the engine's standard. The score only sorts blunders by how avoidable they were.

**It knows nothing about the clock.** Hanging a piece with three seconds left scores the same as hanging it with ten minutes. Time trouble is described separately by the tempo tags (low-clock, hasty, unrushed).

**It is one person's taste, generalized.** The labels come from a single player. The rating adjustment happens through Maia, not through labels from players of every level. The ranking holds up well on unseen blunders, but individual scores will sometimes disagree with your own feeling, especially in the 40% to 70% middle.

**Some blunders have no score.** Mistakes and inaccuracies are never scored, only blunders. A blunder is also left unscored when the stored engine line is too short to tell what happens, or when the human-move model has not been run on the game yet.

---

## 8. Where you see it in FlawChess

**On every blunder.** In the Library, on game cards and on the analysis board, a blunder shows as `?? Blunder` or `??? Facepalm`. Hover or tap it to see the exact score and the type (missed win or allowed loss). Your opponents' blunders are scored too, at *their* rating.

**As a filter.** The Flaws filter has separate Facepalm and Blunder tags. Facepalm lists the blunders at 70% or more, Blunder lists the rest. Select both for all blunders.

**In your statistics.** Library Stats shows your facepalm blunders per 100 of your moves, next to your opponents' in the same games, in total and split into missed wins and allowed losses. The comparison is always like with like: your missed wins against their missed wins, never against their allowed losses. The gap is set against the typical range among FlawChess players for that time control, so you can tell a real difference from noise. The Flaws Timeline shows facepalm blunders as a darker band inside the blunders area, so you can watch the avoidable share change over time.

**In training.** Blunder Check shows short sequences from real games (your own and those of other players at your level) and asks, before each move is played, whether it is a good move or a blunder. The blunders it serves are picked by facepalm score: they have to reach the 70% line for the player who made them. This is the main point of the score. A drill built from blunders nobody could have seen would teach frustration. One built from blunders that *should* have been seen trains the habit of checking before you move.

---

## 9. The whole thing in one paragraph

The Facepalm Score rates each of your blunders from 0% to 100% by how easy it should have been to see for a player of your rating. It combines how much material the move loses, how much the best move would have won, and three human-likelihood estimates from the Maia model at your level: of the move you played, of the best move, and of the opponent's punishing reply. Material is counted the way a player reads a line, after exchanges finish and with the near future weighted most. The weights were fitted to a few hundred blunders hand-labeled as "should have seen it" or "no fair chance." Blunders at 70% or more are facepalm blunders (`???`): they are tagged in your library, compared against your opponents' in your stats, and used to pick the positions for the Blunder Check drill. The score is a ranking of avoidability, not a probability, and it ignores the clock.

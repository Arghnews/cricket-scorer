# ScoreData = recordclass("ScoreData", ["digits", "cell", "val"])
class Scores:
    # We are relying on python 3.7+ here for insertion order guarantee, consider changing to ordered dict
    # in case run on older python installs
    def __init__(self, sheet, scores):
        assert sum(v.digits for v in scores.values()) == 9, "Score digits don't add to 9"
        assert all(isinstance(v.val, int) for v in scores.values()), "Starting score values must be integers"
        self.sheet = sheet
        self.scores = scores

    def update_scores(self):
        unparsable_score_names = []
        for score_name, score_data in self.scores.items():
            # Read the cell value from the spreadsheet
            cell_value = self.sheet.range(score_data.cell).value

            if serialise_score(score_data.digits, cell_value) is None:
                unparsable_score_names.append(score_name)
            else:
                score_data.val = cell_value
        return unparsable_score_names

    def serialise_scores(self):
        return bytes(itertools.chain.from_iterable(
            serialise_score(score_data.digits, score_data.val)
            for score_data in self.scores.values()))

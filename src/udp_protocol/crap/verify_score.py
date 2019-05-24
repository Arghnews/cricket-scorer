#!/usr/bin/env python3

import operator
import sys

def main(argv):
    with open("receiver_score_output.txt", "r") as f:
        scores = list(map(int, f.read().splitlines()))
        print(all(a < b for a, b in zip(scores, scores[1:])))

if __name__ == "__main__":
    sys.exit(main(sys.argv))

import json

languages = {}

with open("text.txt") as f:
    for line in f:
        print(line)
        nextline = next(f)
        #print(nextline)

        languages[nextline.replace("\n", "")] = line.replace("\n", "")

print(languages)
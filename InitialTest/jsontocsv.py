import csv
import re

inputfile = "tocsv.txt"
filename = "model.csv"



with open(filename, 'w', encoding="utf8", newline='') as csvfile:
    fieldnames = ['text', 'label']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    with open(inputfile, encoding="utf8") as input:
        newline = False
        for line in input:
            if not newline:
                var1 = line.rstrip()
                newline = True
            else:
                var2 = line.rstrip()
                writer.writerow({'text': var1, 'label': var2})
                newline = False
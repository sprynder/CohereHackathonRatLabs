import csv
import re

filename = "goemotions_3.csv"
fields = []
rows = []

with open(filename, 'r', encoding="utf8") as csvfile:
    # creating a csv reader object
    csvreader = csv.reader(csvfile)
    # extracting field names through first row
    fields = next(csvreader)
    # extracting each data row one by one
    for row in csvreader:
        rows.append(row)
    print("Total no. of rows: %d"%(csvreader.line_num))

# printing the field names
print('Field names are:' + ', '.join(field for field in fields))
# printing first 5 rows
print('\nFirst 1 rows are:\n')

f = open("testjs.json", "a", encoding="utf8")
f.write("{\n\t\"examples\": [")

p = re.compile('([\"\\\b\f\n\r\t])')
#re.sub(p,'\\1',row[0])

for row in rows:
    #print(row[8])
    for num,field in enumerate(fields[8:]):
        #print(str(num)+"   "+row[num+8]+"   "+field)
        if(row[num+8]=="True" or row[num+8] == "1"):
            s = re.sub(p,r"\\\1",row[0])
            f.write("\t\t{\"text\": \""+ re.sub(r"\\x", r"\\u00", s) + "\", \"label\": \"")
            f.write(field+"\"")
            f.write("},\n")

f.close()

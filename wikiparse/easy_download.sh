set -e
for url in $(python3 ./wikidownloader.py -l=eng -d=late -t=pages-articles -x=xml-PART.bz2 -n=multiple -s); do
   filename=$(basename "$url")
   echo "$filename"
   if ! [ -e $filename ]; then
      wget "$url"
   fi
   python3 ./wikisplitter.py -u "$filename"
   rm "$filename"
done


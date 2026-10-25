#!/usr/bin/env sh
# V3 card pictures at 1632 x 1200 (the split slide's box, 2x), labels >= 70 px. docker run ... video-qa:2 sh video/make_cards.sh
set -eu
F=video/frames
B=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf
RED=0xb71c1c; GREEN=0x1b5e20; INK=0x1f2937; BG=0xeceff4
S=1632x1200
ffmpeg -v error -y -i $F/fit-edit3-blind.png -i $F/fit-edit3-through.png -filter_complex "\
[0:v]scale=1560:-2[a];[1:v]scale=1560:-2[b];color=c=$BG:s=$S[bg];[bg][a]overlay=36:200[t];[t][b]overlay=36:780,\
drawtext=fontfile=$B:text='✗ new hole stops 3 mm short':fontcolor=$RED:fontsize=74:x=40:y=60,\
drawtext=fontfile=$B:text='✓ all three go through':fontcolor=$GREEN:fontsize=74:x=40:y=640" -frames:v 1 $F/card-hook.png
ffmpeg -v error -y -i $F/fit-gap-zoom.png -filter_complex "\
[0:v]scale=-2:1000[a];color=c=$BG:s=$S[bg];[bg][a]overlay=(W-w)/2:180,\
drawtext=fontfile=$B:text='0.2 mm each side':fontcolor=$INK:fontsize=90:x=(w-text_w)/2:y=40" -frames:v 1 $F/card-gap.png
ffmpeg -v error -y -i $F/fit-once1-edit0.png -i $F/fit-once1-edit1.png -i $F/fit-once1-edit2.png -i $F/fit-once1-edit3.png -filter_complex "\
[0:v]scale=1100:-2[a];[1:v]scale=1100:-2[b];[2:v]scale=1100:-2[c];[3:v]scale=1100:-2[d];color=c=$BG:s=$S[bg];\
[bg][a]overlay=500:60[t1];[t1][b]overlay=500:350[t2];[t2][c]overlay=500:640[t3];[t3][d]overlay=500:930,\
drawtext=fontfile=$B:text='start':fontcolor=$INK:fontsize=72:x=40:y=110,\
drawtext=fontfile=$B:text='pegs 6 mm':fontcolor=$INK:fontsize=72:x=40:y=400,\
drawtext=fontfile=$B:text='third peg':fontcolor=$INK:fontsize=72:x=40:y=690,\
drawtext=fontfile=$B:text='plate 8 mm ✓':fontcolor=$INK:fontsize=72:x=40:y=980" -frames:v 1 $F/card-edits.png
echo cards written
ffmpeg -v error -y -i $F/fit-cut-zoom.png -filter_complex "\
[0:v]scale=1560:-2[a];color=c=$BG:s=$S[bg];[bg][a]overlay=36:420,\
drawtext=fontfile=$B:text='middle hole\: cut 5 mm':fontcolor=$RED:fontsize=80:x=(w-text_w)/2:y=60,\
drawtext=fontfile=$B:text='3 mm of plastic left on top':fontcolor=$RED:fontsize=72:x=(w-text_w)/2:y=170,\
drawtext=fontfile=$B:text='outer holes\: go all the way through':fontcolor=$GREEN:fontsize=72:x=(w-text_w)/2:y=1000" -frames:v 1 $F/card-cut.png
ffmpeg -v error -y -i $F/fit-cut-zoom.png -filter_complex "\
[0:v]scale=1040:-2[a];color=c=$BG:s=1080x1920[bg];[bg][a]overlay=20:700,\
drawtext=fontfile=$B:text='Plate made thicker\:':fontcolor=$INK:fontsize=70:x=(w-text_w)/2:y=220,\
drawtext=fontfile=$B:text='do all 3 holes':fontcolor=$INK:fontsize=84:x=(w-text_w)/2:y=330,\
drawtext=fontfile=$B:text='go through?':fontcolor=0x1d4ed8:fontsize=96:x=(w-text_w)/2:y=450,\
drawtext=fontfile=$B:text='red\: 3 mm of plastic':fontcolor=$RED:fontsize=56:x=(w-text_w)/2:y=1150" -frames:v 1 $F/hook-vertical.png
echo cut cards written
# hook-landscape.png: frame 0 of the long video (1920 x 1080), the blind run (roof in red) over a through run
ffmpeg -v error -y -i $F/fit-edit3-blind-red.png -i $F/fit-edit3-through.png -filter_complex "\
[0:v]scale=1720:-2[a];[1:v]scale=1720:-2[b];color=c=$BG:s=1920x1080[bg];[bg][a]overlay=100:190[t];[t][b]overlay=100:670,\
drawtext=fontfile=$B:text='✗ plate made thicker\: the new hole stops 3 mm short':fontcolor=$RED:fontsize=56:x=100:y=70,\
drawtext=fontfile=$B:text='✓ same edit, another run\: all three go through':fontcolor=$GREEN:fontsize=56:x=100:y=550,\
drawtext=fontfile=$B:text='cut open through the pegs, from the front · our drawing from the saved designs, not a print':fontcolor=$INK:fontsize=28:x=(w-text_w)/2:y=1030" \
  -frames:v 1 $F/hook-landscape.png
echo hook-landscape written

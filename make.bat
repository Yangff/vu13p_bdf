xsdata ./dtd/board.dtd --package generated.board
xsdata ./dtd/preset.dtd --package generated.preset
xsdata ./dtd/part0_pins.dtd --package generated.part0_pins

python3 ./scr/main.py

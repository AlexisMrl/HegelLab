class IdxIter:
    # return custom indexes for filling an array in a certain way
    # array = [ [a,b], [c,d], ... ]
    # array[2,1] = c

    # this is not an iterator btw, it just counts

    def __init__(self, nb_cols, nb_rows, reverse_cols=False, reverse_rows=False, alternate=False):
        # reverse_xxx is True if sweep start > sweep stop
        self.nb_cols = nb_cols - 1
        self.nb_rows = nb_rows - 1
        self.reverse_cols = reverse_cols
        self.reverse_rows = reverse_rows
        self.alternate = alternate
        self.reset()

    def reset(self):
        self.current_col = self.nb_cols if self.reverse_cols else 0
        self.current_row = self.nb_rows if self.reverse_rows else 0

    def next(self):
        col, row = self.current_col, self.current_row
        rev_col, rev_row = self.reverse_cols, self.reverse_rows
        nb_rows = self.nb_rows
        alternate = self.alternate

        row = row - 1 if rev_row else row + 1

        if row < 0:
            if alternate:
                row = 0
                self.reverse_rows = not self.reverse_rows
            else:
                row = nb_rows
            col = col - 1 if rev_col else col + 1

        elif row > nb_rows:
            if alternate:
                row = nb_rows
                self.reverse_rows = not self.reverse_rows
            else:
                row = 0
            col = col - 1 if rev_col else col + 1

        # if col < 0 or col > self.nb_cols:
        # raise StopIteration

        self.current_row, self.current_col = row, col
        return col, row

    def current(self):
        tmp_col, tmp_row = self.current_col, self.current_row
        return tmp_col, tmp_row

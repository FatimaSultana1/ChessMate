import chess

def fen_to_board_dict(fen):
    board = chess.Board(fen)
    board_dict = []
    unicode_pieces = {
        'r': '&#9820;', 'n': '&#9822;', 'b': '&#9821;', 'q': '&#9819;',
        'k': '&#9818;', 'p': '&#9823;', 'R': '&#9814;', 'N': '&#9816;',
        'B': '&#9815;', 'Q': '&#9813;', 'K': '&#9812;', 'P': '&#9817;'
    }
    for rank in range(8, 0, -1):
        row = {}
        for file in 'abcdefgh':
            square = chess.parse_square(f"{file}{rank}")
            piece = board.piece_at(square)
            if piece:
                symbol = piece.symbol()
                row[f"{file}{rank}"] = unicode_pieces.get(symbol, symbol)
            else:
                row[f"{file}{rank}"] = '&nbsp;'
        board_dict.append(row)
    return board_dict

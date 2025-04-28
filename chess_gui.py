import pygame
import os
import threading
import time
from chess import Chess

class ChessGUI:
    def __init__(self):
        pygame.init()
        self.SQUARE_SIZE = 80
        self.BOARD_SIZE = self.SQUARE_SIZE * 8
        self.MARGIN = 40  # Margin for coordinates
        self.WINDOW_SIZE = (self.BOARD_SIZE + 2*self.MARGIN, self.BOARD_SIZE + self.MARGIN + 100)  # Extra space for coordinates and suggestions
        self.screen = pygame.display.set_mode(self.WINDOW_SIZE)
        pygame.display.set_caption("Chess Game")
        
        # Initialize the chess engine
        self.chess_game = Chess()
        
        # Load images
        self.load_images()
        
        # Drag and drop variables
        self.selected_piece = None
        self.dragging = False
        self.drag_pos = None
        self.last_move = None  # Store the last move made
        
        # AI suggestion variables
        self.alpha_beta_suggestion = None
        self.evolutionary_suggestion = None
        self.suggestion_lock = threading.Lock()
        
        # Start AI suggestion threads
        self.running = True
        self.alpha_beta_thread = threading.Thread(target=self.update_alpha_beta_suggestions)
        self.evolutionary_thread = threading.Thread(target=self.update_evolutionary_suggestions)
        self.alpha_beta_thread.daemon = True
        self.evolutionary_thread.daemon = True
        self.alpha_beta_thread.start()
        self.evolutionary_thread.start()

    def load_images(self):
        """Load piece images from the 'pieces' folder"""
        self.pieces = {}
        piece_chars = {'P': 'white-pawn', 'R': 'white-rook', 'N': 'white-knight',
                      'B': 'white-bishop', 'Q': 'white-queen', 'K': 'white-king',
                      'p': 'black-pawn', 'r': 'black-rook', 'n': 'black-knight',
                      'b': 'black-bishop', 'q': 'black-queen', 'k': 'black-king'}
        
        try:
            for piece, filename in piece_chars.items():
                image_path = os.path.join('pieces', f'{filename}.png')
                self.pieces[piece] = pygame.transform.scale(
                    pygame.image.load(image_path),
                    (self.SQUARE_SIZE, self.SQUARE_SIZE)
                )
        except pygame.error as e:
            print(f"Couldn't load piece images: {e}")
            print("Make sure you have a 'pieces' folder with the required PNG images")
            exit(1)

    def get_square_from_pos(self, pos):
        """Convert screen position to board coordinates"""
        x, y = pos
        file = (x - self.MARGIN) // self.SQUARE_SIZE
        rank = y // self.SQUARE_SIZE
        if 0 <= file < 8 and 0 <= rank < 8:
            return f"{chr(file + 97)}{8 - rank}"
        return None

    def get_piece_at_pos(self, pos):
        """Get the piece at the given screen position"""
        square = self.get_square_from_pos(pos)
        if square:
            board_pos = self.chess_game.board_2_array(square)
            if board_pos:
                piece = self.chess_game.board[board_pos[1]][board_pos[0]]
                # Only allow selecting pieces of the current player's color
                if piece != 0 and ((self.chess_game.p_move == 1 and piece > 0) or 
                                 (self.chess_game.p_move == -1 and piece < 0)):
                    return square
        return None

    def draw_board(self):
        """Draw the chess board with coordinates"""
        # Draw coordinates
        font = pygame.font.Font(None, 36)
        
        # Draw rank numbers (1-8)
        for rank in range(8):
            text = font.render(str(8 - rank), True, (0, 0, 0))
            self.screen.blit(text, (self.MARGIN//2 - text.get_width()//2, 
                                  rank * self.SQUARE_SIZE + self.SQUARE_SIZE//2 - text.get_height()//2))
            
        # Draw file letters (a-h)
        for file in range(8):
            text = font.render(chr(file + 97), True, (0, 0, 0))
            self.screen.blit(text, (self.MARGIN + file * self.SQUARE_SIZE + self.SQUARE_SIZE//2 - text.get_width()//2,
                                  8 * self.SQUARE_SIZE + 5))
        
        # Draw the board squares
        for rank in range(8):
            for file in range(8):
                color = (255, 206, 158) if (rank + file) % 2 == 0 else (209, 139, 71)
                rect = pygame.Rect(self.MARGIN + file * self.SQUARE_SIZE, 
                                 rank * self.SQUARE_SIZE,
                                 self.SQUARE_SIZE, 
                                 self.SQUARE_SIZE)
                pygame.draw.rect(self.screen, color, rect)
                
                # Highlight last move if exists
                if self.last_move:
                    start_pos = self.chess_game.board_2_array(self.last_move[0])
                    end_pos = self.chess_game.board_2_array(self.last_move[1])
                    if (file, rank) in [start_pos, end_pos]:
                        highlight = pygame.Surface((self.SQUARE_SIZE, self.SQUARE_SIZE))
                        highlight.set_alpha(128)
                        highlight.fill((255, 255, 0))
                        self.screen.blit(highlight, (self.MARGIN + file * self.SQUARE_SIZE, rank * self.SQUARE_SIZE))

    def draw_pieces(self):
        """Draw all pieces on the board"""
        for rank in range(8):
            for file in range(8):
                piece = self.chess_game.board[rank][file]
                if piece != 0:
                    piece_char = self.get_piece_char(piece)
                    if piece_char in self.pieces and (file, rank) != self.selected_piece:
                        self.screen.blit(self.pieces[piece_char],
                                       (self.MARGIN + file * self.SQUARE_SIZE,
                                        rank * self.SQUARE_SIZE))

    def get_piece_char(self, piece):
        """Convert piece number to character representation"""
        piece_chars = {1: 'P', 2: 'N', 3: 'B', 4: 'R', 5: 'Q', 6: 'K',
                      -1: 'p', -2: 'n', -3: 'b', -4: 'r', -5: 'q', -6: 'k'}
        return piece_chars.get(piece, '')

    def draw_suggestions(self):
        """Draw AI move suggestions"""
        # Draw background for suggestions
        pygame.draw.rect(self.screen, (240, 240, 240), 
                        (0, self.BOARD_SIZE + self.MARGIN, 
                         self.BOARD_SIZE + 2*self.MARGIN, 100))
        
        # Draw suggestions text
        font = pygame.font.Font(None, 24)
        
        with self.suggestion_lock:
            if self.alpha_beta_suggestion:
                text = f"Alpha-Beta: {self.alpha_beta_suggestion[0]} → {self.alpha_beta_suggestion[1]}"
                text_surface = font.render(text, True, (0, 0, 0))
                self.screen.blit(text_surface, (10, self.BOARD_SIZE + self.MARGIN + 20))
            
            if self.evolutionary_suggestion:
                text = f"Evolutionary: {self.evolutionary_suggestion[0]} → {self.evolutionary_suggestion[1]}"
                text_surface = font.render(text, True, (0, 0, 0))
                self.screen.blit(text_surface, (10, self.BOARD_SIZE + self.MARGIN + 60))

    def update_alpha_beta_suggestions(self):
        """Continuously update alpha-beta pruning suggestions"""
        while self.running:
            if not self.dragging:
                suggestion = self.chess_game.get_alpha_beta_move()
                with self.suggestion_lock:
                    self.alpha_beta_suggestion = suggestion
            time.sleep(1)  # Update every second

    def update_evolutionary_suggestions(self):
        """Continuously update evolutionary algorithm suggestions"""
        while self.running:
            if not self.dragging:
                suggestion = self.chess_game.evolutionary_algorithm()
                with self.suggestion_lock:
                    self.evolutionary_suggestion = suggestion
            time.sleep(1)  # Update every second

    def run(self):
        """Main game loop"""
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    self.running = False
                
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        pos = event.pos
                        square = self.get_piece_at_pos(pos)
                        if square:
                            self.selected_piece = square
                            self.dragging = True
                            self.drag_pos = pos
                
                elif event.type == pygame.MOUSEBUTTONUP:
                    if event.button == 1 and self.dragging:
                        pos = event.pos
                        target_square = self.get_square_from_pos(pos)
                        if target_square and self.selected_piece:
                            # Attempt to make the move
                            if self.chess_game.move(self.selected_piece, target_square):
                                self.last_move = (self.selected_piece, target_square)  # Store the last move
                                state = self.chess_game.is_end()
                                if sum(state) > 0:
                                    print("Game Over!")
                                    running = False
                                    break
                        self.selected_piece = None
                        self.dragging = False
                
                elif event.type == pygame.MOUSEMOTION:
                    self.drag_pos = event.pos

            # Draw the game state
            self.screen.fill((255, 255, 255))  # Clear screen with white background
            self.draw_board()
            self.draw_pieces()
            
            # Draw dragged piece
            if self.dragging and self.selected_piece:
                board_pos = self.chess_game.board_2_array(self.selected_piece)
                piece = self.chess_game.board[board_pos[1]][board_pos[0]]
                piece_char = self.get_piece_char(piece)
                if piece_char in self.pieces:
                    x, y = self.drag_pos
                    self.screen.blit(self.pieces[piece_char],
                                   (x - self.SQUARE_SIZE//2, y - self.SQUARE_SIZE//2))
            
            # Draw suggestions
            self.draw_suggestions()
            
            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    gui = ChessGUI()
    gui.run()
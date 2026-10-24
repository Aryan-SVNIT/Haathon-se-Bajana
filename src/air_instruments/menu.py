"""Startup instrument picker."""
import pygame


def choose_instrument() -> str | None:
    """Return ``'piano'``, ``'guitar'`` or ``None`` if the user closes the menu."""
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_caption("Air Instruments | Choose an instrument")
    screen = pygame.display.set_mode((720, 420))
    clock = pygame.time.Clock()
    title_font = pygame.font.Font(None, 52)
    subtitle_font = pygame.font.Font(None, 27)
    button_font = pygame.font.Font(None, 40)
    small_font = pygame.font.Font(None, 23)

    piano_rect = pygame.Rect(90, 175, 245, 145)
    guitar_rect = pygame.Rect(385, 175, 245, 145)
    background = (21, 27, 42)

    try:
        while True:
            mouse_pos = pygame.mouse.get_pos()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_ESCAPE, pygame.K_q):
                        return None
                    if event.key == pygame.K_p:
                        return "piano"
                    if event.key == pygame.K_g:
                        return "guitar"
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if piano_rect.collidepoint(event.pos):
                        return "piano"
                    if guitar_rect.collidepoint(event.pos):
                        return "guitar"

            screen.fill(background)
            title = title_font.render("Choose your instrument", True, (245, 247, 255))
            subtitle = subtitle_font.render("Click a card below, or press P / G", True, (180, 192, 211))
            screen.blit(title, title.get_rect(center=(360, 72)))
            screen.blit(subtitle, subtitle.get_rect(center=(360, 120)))

            piano_hover = piano_rect.collidepoint(mouse_pos)
            guitar_hover = guitar_rect.collidepoint(mouse_pos)
            piano_fill = (67, 116, 185) if piano_hover else (48, 83, 137)
            guitar_fill = (44, 139, 106) if guitar_hover else (32, 102, 79)
            pygame.draw.rect(screen, piano_fill, piano_rect, border_radius=18)
            pygame.draw.rect(screen, guitar_fill, guitar_rect, border_radius=18)
            pygame.draw.rect(screen, (225, 232, 245), piano_rect, width=2, border_radius=18)
            pygame.draw.rect(screen, (225, 232, 245), guitar_rect, width=2, border_radius=18)

            screen.blit(button_font.render("PIANO", True, (255, 255, 255)),
                        button_font.render("PIANO", True, (255, 255, 255)).get_rect(center=(piano_rect.centerx, 225)))
            screen.blit(small_font.render("Two hands / 10 notes", True, (235, 240, 250)),
                        small_font.render("Two hands / 10 notes", True, (235, 240, 250)).get_rect(center=(piano_rect.centerx, 270)))
            screen.blit(button_font.render("GUITAR", True, (255, 255, 255)),
                        button_font.render("GUITAR", True, (255, 255, 255)).get_rect(center=(guitar_rect.centerx, 225)))
            screen.blit(small_font.render("One hand / 5 notes", True, (235, 250, 243)),
                        small_font.render("One hand / 5 notes", True, (235, 250, 243)).get_rect(center=(guitar_rect.centerx, 270)))

            footer = small_font.render("Bend a finger to play | Q / Esc to close", True, (180, 192, 211))
            screen.blit(footer, footer.get_rect(center=(360, 370)))
            pygame.display.flip()
            clock.tick(60)
    finally:
        # OpenCV owns the camera-window display after a selection is made.
        pygame.display.quit()

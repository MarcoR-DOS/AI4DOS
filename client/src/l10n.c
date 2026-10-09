/* Fixed DOS byte resources, shared CP437/CP850 German letters. No heap,
   runtime files or Unicode decoder. Octal escapes keep compiler input ASCII. */
#include <string.h>
#include "l10n.h"
static Language current_language=LANG_EN;
static unsigned current_codepage;
static const char * const texts[LANG_COUNT][TXT_COUNT]={
    {
        "Help", /* HELP */
        "ESC Back", /* BACK */
        "Connecting", /* CONNECTING */
        "Online", /* ONLINE */
        "TX/RX", /* TX_RX */
        "Error", /* ERROR */
        "F2 New chat", /* NEW_CHAT */
        "F4 Help", /* HELP_KEY */
        "F5 Save", /* SAVE */
        "F10 Exit", /* EXIT */
        "Version", /* VERSION */
        "Session", /* SESSION */
        "Status", /* STATUS */
        "Server", /* SERVER */
        "Connected", /* CONNECTED */
        "Disconnected", /* DISCONNECTED */
        "You", /* USER */
        "AI", /* AI */
        "System", /* SYSTEM */
        "Enter                Send message", /* HELP_SEND */
        "F2 or /new           New chat", /* HELP_NEW */
        "F4 or /help          Help", /* HELP_HELP */
        "F5 or /save          Save chat", /* HELP_SAVE */
        "F10 or /quit         Exit (with confirmation)", /* HELP_EXIT */
        "PgUp/PgDn            Scroll by page", /* HELP_PAGES */
        "Up/Down arrows       Scroll by line", /* HELP_LINES */
        "F1 or /info          Info", /* HELP_INFO */
        "ESC                  Back to chat", /* HELP_BACK */
        "Save as: ", /* SAVE_AS */
        "ENTER Save   ESC Cancel", /* SAVE_HINT */

        "Invalid filename (1-8 chars, optional .1-3; A-Z/0-9/_/-). ESC Cancel", /* SAVE_INVALID */
        "Exit now?  F10 = Yes   ESC = Cancel", /* EXIT_CONFIRM */
        "Usage: AI4DOS config.cfg [DOS message]\nConfiguration invalid or missing.\n", /* USAGE */
        "Cannot establish 80x25 text mode.\n", /* VIDEO_FAILED */
        "Network read failed.\n", /* READ_FAILED */
        "Connect failed.\n", /* CONNECT_FAILED */
        "Unexpected protocol frame.\n", /* UNEXPECTED_FRAME */
        "Network disconnected while waiting for input.\n", /* INPUT_DISCONNECTED */
        "Message exceeds the 1000 UTF-8 byte limit.\n", /* MESSAGE_LENGTH */
        "Invalid control character in message.\n", /* ASCII_ONLY */
        "Invalid reply frame.\n", /* INVALID_REPLY */
        "Connection/protocol failed or cancelled.\n", /* FAILED */
        "AI4DOS UI scripted chat completed.", /* SCRIPT_DONE */
        "AI4DOS Wire Protocol", /* WIRE_PROTOCOL */
        "Saved: ", /* SAVED */
        "File exists. Overwrite? F5 Yes   ESC Cancel", /* SAVE_OVERWRITE */
        "Cannot create CHATS directory. ENTER Retry   ESC Cancel", /* SAVE_DIRECTORY */
        "Save failed. ENTER Retry   ESC Cancel", /* SAVE_ERROR */
        "Transcript almost full. F5 Save chat   F2 New chat", /* TRANSCRIPT_WARNING */
        "Transcript full. F5 Save chat   F2 New chat", /* TRANSCRIPT_FULL */
        "Use /reconnect to try again.",
        "Response interrupted. /reconnect to continue the chat.",
        "Session unavailable. F5 Save; F2 New chat; /reconnect retry",
        "Session busy. /reconnect to retry later; F5 Save",
        "/reconnect           Reconnect and resume session",
        "Connecting to gateway...",
        "Connected. You can start chatting.",
        "Gateway unreachable.",
        "Authentication failed.",
        "Connection lost.",
        "Connection restored.",
        "Network unavailable.",
        "Packet driver not found or initialization failed. Check PACKETINT.",
        "Check MTCPCFG and IP configuration.",
        "Network stack initialization failed. See diagnostic above.",
        "Network not configured.",
        "No valid IP address assigned.",
        "Run DHCP or check your IP configuration.",
        "Invalid server address. Check SERVER in AI4DOS.CFG.",
        "Network gateway not configured. Check your mTCP IP configuration.",
    },
    {
        "Hilfe", /* HELP */
        "ESC Zur\201ck", /* BACK */
        "Verbindungsaufbau", /* CONNECTING */
        "Online", /* ONLINE */
        "TX/RX", /* TX_RX */
        "Fehler", /* ERROR */
        "F2 Neuer Chat", /* NEW_CHAT */
        "F4 Hilfe", /* HELP_KEY */
        "F5 Speichern", /* SAVE */
        "F10 Beenden", /* EXIT */
        "Version", /* VERSION */
        "Sitzung", /* SESSION */
        "Status", /* STATUS */
        "Server", /* SERVER */
        "Verbunden", /* CONNECTED */
        "Getrennt", /* DISCONNECTED */
        "Du", /* USER */
        "KI", /* AI */
        "System", /* SYSTEM */
        "Enter                Nachricht senden", /* HELP_SEND */
        "F2 oder /new         Neuer Chat", /* HELP_NEW */
        "F4 oder /help        Hilfe", /* HELP_HELP */
        "F5 oder /save        Chat speichern", /* HELP_SAVE */
        "F10 oder /quit       Beenden (mit Best\204tigung)", /* HELP_EXIT */
        "PgUp/PgDn            Seitenweise im Verlauf", /* HELP_PAGES */
        "Pfeil hoch/runter    Zeilenweise im Verlauf", /* HELP_LINES */
        "F1 oder /info        Info", /* HELP_INFO */
        "ESC                  Zur\201ck zum Chat", /* HELP_BACK */
        "Speichern als: ", /* SAVE_AS */
        "ENTER Speichern   ESC Abbrechen", /* SAVE_HINT */

        "Ung\201ltiger Dateiname (1-8, optional .1-3; A-Z/0-9/_/-). ESC Abbrechen", /* SAVE_INVALID */
        "Wirklich beenden?  F10 = Ja   ESC = Abbrechen", /* EXIT_CONFIRM */
        "Aufruf: AI4DOS config.cfg [DOS-Nachricht]\nKonfiguration fehlt oder ist ung\201ltig.\n", /* USAGE */
        "80x25-Textmodus konnte nicht gestartet werden.\n", /* VIDEO_FAILED */
        "Lesen vom Netzwerk fehlgeschlagen.\n", /* READ_FAILED */
        "Verbindung fehlgeschlagen.\n", /* CONNECT_FAILED */
        "Unerwarteter Protokollrahmen.\n", /* UNEXPECTED_FRAME */
        "Netzwerkverbindung w\204hrend der Eingabe getrennt.\n", /* INPUT_DISCONNECTED */
        "Nachricht ueberschreitet das Limit von 1000 UTF-8-Bytes.\n", /* MESSAGE_LENGTH */
        "Ungueltiges Steuerzeichen in der Nachricht.\n", /* ASCII_ONLY */
        "Ung\201ltiger Antwortrahmen.\n", /* INVALID_REPLY */
        "Verbindung/Protokoll fehlgeschlagen oder abgebrochen.\n", /* FAILED */
        "AI4DOS UI-Testchat abgeschlossen.", /* SCRIPT_DONE */
        "AI4DOS Wire-Protokoll", /* WIRE_PROTOCOL */
        "Gespeichert: ", /* SAVED */
        "Datei existiert. \232berschreiben? F5 Ja   ESC Abbrechen", /* SAVE_OVERWRITE */
        "CHATS kann nicht angelegt werden. ENTER Wiederholen   ESC Abbrechen", /* SAVE_DIRECTORY */
        "Speichern fehlgeschlagen. ENTER Wiederholen   ESC Abbrechen", /* SAVE_ERROR */
        "Chatverlauf fast voll. F5 Speichern   F2 Neuer Chat", /* TRANSCRIPT_WARNING */
        "Chatverlauf voll. F5 Speichern   F2 Neuer Chat", /* TRANSCRIPT_FULL */
        "Mit /reconnect kannst du es erneut versuchen.",
        "Antwort abgebrochen. /reconnect zum Fortsetzen des Chats.",
        "Sitzung fehlt. F5 Speichern; F2 Neuer Chat; /reconnect erneut",
        "Sitzung belegt. /reconnect sp\204ter erneut; F5 Speichern",
        "/reconnect           Verbinden und Sitzung fortsetzen",
        "Verbinde mit Gateway...",
        "Verbunden. Du kannst jetzt chatten.",
        "Gateway nicht erreichbar.",
        "Authentifizierung fehlgeschlagen.",
        "Verbindung getrennt.",
        "Verbindung wiederhergestellt.",
        "Netzwerk nicht verfuegbar.",
        "Packet Driver fehlt oder Start fehlgeschlagen. PACKETINT pruefen.",
        "MTCPCFG und IP-Konfiguration pruefen.",
        "Netzwerkstart fehlgeschlagen. Siehe Diagnose oben.",
        "Netzwerk nicht konfiguriert.",
        "Keine gueltige IP-Adresse zugewiesen.",
        "DHCP ausfuehren oder IP-Konfiguration pruefen.",
        "Ungueltige Serveradresse. SERVER in AI4DOS.CFG pruefen.",
        "IP-Gateway nicht konfiguriert. mTCP IP-Konfiguration pruefen.",
    },
};
Language language_parse(const char *value)
{return value&&strcmp(value,"de")==0?LANG_DE:LANG_EN;}
void language_set(Language language)
{current_language=(unsigned)language<LANG_COUNT?language:LANG_EN;}
Language language_get(void){return current_language;}
void language_codepage(unsigned codepage){current_codepage=codepage;}
const char *tr(TextId id)
{
    if((unsigned)id>=TXT_COUNT)return "";
    if(current_language==LANG_DE&&current_codepage!=437&&current_codepage!=850){
        switch(id){
        case TXT_SESSION_BUSY:return "Sitzung belegt. /reconnect spaeter erneut; F5 Speichern";
        case TXT_BACK:return "ESC Zurueck";
        case TXT_HELP_EXIT:return "F10 oder /quit       Beenden (mit Bestaetigung)";
        case TXT_HELP_BACK:return "ESC                  Zurueck zum Chat";
        case TXT_SAVE_OVERWRITE:return "Datei existiert. Ueberschreiben? F5 Ja   ESC Abbrechen";
        case TXT_SAVE_INVALID:return "Ungueltiger Dateiname (1-8, optional .1-3; A-Z/0-9/_/-). ESC Abbrechen";
        case TXT_USAGE:return "Aufruf: AI4DOS config.cfg [DOS-Nachricht]\nKonfiguration fehlt oder ist ungueltig.\n";
        case TXT_INPUT_DISCONNECTED:return "Netzwerkverbindung waehrend der Eingabe getrennt.\n";
        case TXT_INVALID_REPLY:return "Ungueltiger Antwortrahmen.\n";
        default:break;
        }
    }
    return texts[current_language][id];
}

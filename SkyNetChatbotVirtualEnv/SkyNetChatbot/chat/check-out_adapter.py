import datetime
import requests

from chat.custom_logic_adapter_model import CustomLogicAdapter
from chatterbot.conversation import Statement
from chat.lev_dist import lev_dist, lev_dist_custom_dist
import re


class CheckOutAdapter(CustomLogicAdapter):

    def __init__(self, chatbot, **kwargs):
        super().__init__(chatbot, **kwargs)
        self.sede = None
        self.date = datetime.date.today()

    def can_process(self, statement):
        check_out_words = ['check-out', 'checkout', 'check out', 'lasciare', 'andare via', 'tornare a casa', 'partire']

        input_words = re.sub(r"[^a-zA-Z0-9 \n.\-/]", ' ', statement.text).split()

        if self.processing_stage is not None:
            return True

        if lev_dist(input_words, check_out_words):
            self.processing_stage = "check-out"
            return True
        else:
            return False

    def process(self, statement, additional_response_selection_parameters=None):
        confirm_wrong_response = "Non ho capito! Prova a dirmi 'Sì' o 'No'."
        confirm_response = "Effettuare il check-out nella sede di "
        checkout_done_response = "Hai già fatto il check-out!"
        api_error_response = "Errore nella richiesta dei dati! Verifica di aver inserito le credenziali corrette!"
        success_response = "Check-out effettuato correttamente nella sede di "
        exit_response = "Check-out annullato"

        # Test API Key
        api_key = '87654321-4321-4321-4321-210987654321'

        # Check if user wants to exit
        if self.check_exit(statement):
            self.processing_stage = None
            response = Statement(exit_response)
            response.confidence = 1
            return response

        # Check-out processing stages
        if self.processing_stage == "check-out":
            # Check if the user is already checked-out with API
            url = 'https://apibot4me.imolinfo.it/v1/locations/presence/me'
            service_response = requests.get(url, headers={'api_key': api_key})
            print("checkout imolinfo locations presence me: " + str(service_response.json()))  # LOG
            if service_response.status_code == 404:
                response_text = checkout_done_response
                self.processing_stage = None
            else:
                self.processing_stage = "check-out confirm"
                self.sede = service_response.json()['location']
                response_text = confirm_response + self.sede + "?"
            confidence = 0.5
        elif self.processing_stage == "check-out confirm":
            yes_words = ["sì", "si", "ok", "yes", "s", "y", "vai"]
            no_words = ["no", "n", "nope"]
            if lev_dist_custom_dist(statement.text.split(), yes_words, 0):
                # Check-out the user in the selected 'sede' with API
                url = 'https://apibot4me.imolinfo.it/v1/locations/' + self.sede + '/presence'
                service_response = requests.delete(url, headers={"api_key": api_key,
                                                                 "Content-Type": "application/json"})
                self.processing_stage = None
                if service_response.status_code == 204:
                    response_text = success_response + self.sede
                else:
                    response_text = api_error_response + "\nError status code: " + str(service_response.status_code)
                    # + ": " + service_response.json()['error']
            elif lev_dist_custom_dist(statement.text.split(), no_words, 0):
                response_text = exit_response
                self.processing_stage = None
            else:
                response_text = confirm_wrong_response + "\n" + confirm_response + self.sede + "?"
            confidence = 1
        else:  # Non dovrebbe mai arrivare qui
            self.processing_stage = None
            response_text = "Errore interno! Riprovare ad effettuare l'operazione."
            confidence = 1

        response = Statement(response_text)
        response.confidence = confidence
        return response

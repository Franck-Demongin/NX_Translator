import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";
import { api } from "../../scripts/api.js"

app.registerExtension({
	name: "Nx_Translator",	
	
	async beforeRegisterNodeDef(nodeType, nodeData, app) {		
		if (nodeData.name === "Nx_Translator") {			
			const orig_nodeCreated = nodeType.prototype.onNodeCreated;

	        nodeType.prototype.onNodeCreated = function () {
				orig_nodeCreated?.apply(this, arguments);
				
				this.label = "Translate";

				// get usage
				this.get_usage = async () => {
					const resp = await api.fetchApi('/deeplusage', {method: 'GET'})
					return resp					
				}

				// get token
				this.token_get = async () => {
					const resp = await api.fetchApi('/deeplgettoken', {	method: 'GET'})
					return resp	
				}

				// set token
				this.token_set = async (token) => {
					if (token === null) {
						token = ""
					}
					let tk = prompt('Your token DeepL', token);
					if (tk === null) {
						return
					} 
					else if (tk === "") {
						alert("Empty token is not allowed");
						return
					}
					
					await api.fetchApi('/deeplsettoken', {
						method: 'POST',
						body: JSON.stringify({"token": tk}),
					})
					.then(response => response.json())
					.then(data => {
						if (!data.saved) {
							alert("Error: one error occurred")
						}
						this.token = tk
						this.update_btn_translate()
					})
					.catch(error => {
						console.error('Error:', error);
					})
				}

				// translate text
				this.translate = async (message, translator) => {
					console.log(message, translator)
					if (translator === 'DeepL') {
						const resp1 = await api.fetchApi('/deepltranslate', {
							method: 'POST',
							body: JSON.stringify(message),
						})
						return resp1
					}
					else {
						const resp2 = await api.fetchApi('/googletranslate', {
							method: 'POST',
							body: JSON.stringify(message),
						})	
						return resp2
					}
				}

				this.set_label = (btn, data) => {
					var label = "⬇ Enter valid token ⬇"
					var tr = this.widgets?.find((w) => w.name === "translator");
					var translator = tr.value
					console.log('translator', translator)
					if((data.used) && translator === "DeepL") {
						label = "🔀 Translate (" + new Intl.NumberFormat().format(data.used[0]) + "/" + new Intl.NumberFormat().format(data.used[1]) + ")";
					}
					else if(translator === "Google Translate") {
						label = "🔀 Translate"
					}
					btn.label = label
				}

				// upadate label on button Translate
				this.update_btn_translate = () => {
					this.get_usage() 
					.then(response => response.json())
					.then(data => {
						this.set_label(this.button, data)
					})
					.catch(error => {
						console.error('Error:', error);
					});
				}

				// callback on translator engine change. Used to update label on button Translate
				const translatorWidget = this.widgets?.find((w) => w.name === "translator");	
				translatorWidget.callback = async (v) => {
					this.update_btn_translate()
				}

				console.log(this)
				// create widgets button Translate
				this.button = this.addWidget("button", "🔀 Translate", null, () => {	
					this.translator = this.widgets?.find((w) => w.name === "translator");					
					this.prompt = this.widgets?.find((w) => w.name === "prompt");
					this.text = this.widgets?.find((w) => w.name === "text");
					this.mode = this.widgets?.find((w) => w.name === "mode");
					this.sep = this.widgets?.find((w) => w.name === "sep");

					const translator = this.translator.value
						
					if(this.prompt.value.trim().length === 0) {
						this.text.value = "";
						return
					}
					this.text_value = this.text.value;
					this.text.value = "Translating...";
					this.translate({"prompt": this.prompt.value}, translator)
					.then(response => response.json())
					.then(data => {
						const sep_liste = {
							"comma": ", ",
							"space": " ",
							"newline": "\n",
							"none": ""
						}
						const sep = sep_liste[this.sep.value];
						if (!data.token_valid) {
							this.text.value = data.text;
						}
						else if (this.mode.value == "append") {
							this.text.value = this.text_value + sep + data.text;
						}
						else if (this.mode.value == "prepend") {
							this.text.value =  data.text + sep + this.text_value;
						}
						else {
							this.text.value = data.text;
						}
						this.update_btn_translate()
					})
				}, { serialize: false });	
				
				this.update_btn_translate();
				
				// create widgets button Token DeepL
				this.buttonToken = this.addWidget("button", "Token DeepL", null, () => {
					let tk = this.token_get()
					.then(response => response.json())
					.then(data => {
						this.token_set(data.token)
					})
					.catch(error => {
						console.error('Error:', error);
					});
				}, { serialize: false })

				nodeType.prototype.shape = "box";
				this.size = [400, 350];
			}	
		}
	}
});
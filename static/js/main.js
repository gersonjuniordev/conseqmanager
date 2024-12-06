document.addEventListener('DOMContentLoaded', function() {
    const uploadForm = document.getElementById('uploadForm');
    const result = document.getElementById('result');
    const qrcodeDiv = document.getElementById('qrcode');
    const signLink = document.getElementById('signLink');
    const shareWhatsApp = document.getElementById('shareWhatsApp');
    
    if (uploadForm) {
        // Prevenir o comportamento padrão do drag and drop
        const dropZone = document.getElementById('dropZone');
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        // Adicionar/remover classe quando arrastar arquivo
        ['dragenter', 'dragover'].forEach(eventName => {
            dropZone.addEventListener(eventName, highlight, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, unhighlight, false);
        });

        function highlight(e) {
            dropZone.classList.add('dragover');
        }

        function unhighlight(e) {
            dropZone.classList.remove('dragover');
        }

        // Manipular o drop de arquivos
        dropZone.addEventListener('drop', handleDrop, false);

        function handleDrop(e) {
            const dt = e.dataTransfer;
            const files = dt.files;
            handleFiles(files);
        }

        function handleFiles(files) {
            if (files.length > 0) {
                document.getElementById('pdf').files = files;
                document.getElementById('fileName').textContent = files[0].name;
            }
        }

        // Manipular o upload do formulário
        uploadForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const formData = new FormData(this);
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // Mostrar QR Code
                    qrcodeDiv.innerHTML = `<img src="data:image/png;base64,${data.qr_code}">`;
                    
                    // Mostrar link
                    signLink.textContent = data.sign_url;
                    
                    // Configurar botão do WhatsApp
                    const phone = formData.get('phone').replace(/\D/g, '');
                    shareWhatsApp.onclick = function() {
                        const text = encodeURIComponent(`Por favor, assine o documento no link: ${data.sign_url}`);
                        window.open(`https://wa.me/${phone}?text=${text}`);
                    };
                    
                    // Mostrar resultado e esconder formulário
                    result.style.display = 'block';
                    uploadForm.style.display = 'none';
                } else {
                    alert(data.error || 'Erro ao enviar documento');
                }
            } catch (error) {
                console.error('Erro:', error);
                alert('Erro ao enviar documento');
            }
        });

        // Atualizar nome do arquivo quando selecionado
        document.getElementById('pdf').addEventListener('change', function() {
            const fileName = this.files[0] ? this.files[0].name : 'Nenhum arquivo selecionado';
            document.getElementById('fileName').textContent = fileName;
        });
    }
});

// Função para copiar link
function copyLink() {
    const signLink = document.getElementById('signLink');
    navigator.clipboard.writeText(signLink.textContent)
        .then(() => {
            alert('Link copiado com sucesso!');
        })
        .catch(err => {
            console.error('Erro ao copiar link:', err);
        });
}

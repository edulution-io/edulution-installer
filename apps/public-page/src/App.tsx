import { useState, useRef, useCallback } from 'react';
import { Button } from '@edulution-io/ui-kit';
import { Card, CardContent } from '@shared-ui';

const INSTALL_COMMAND = 'bash <(curl -s https://get.edulution.io/installer)';

const App = () => {
  const [copied, setCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(INSTALL_COMMAND);
    } catch {
      if (inputRef.current) {
        inputRef.current.select();
        inputRef.current.setSelectionRange(0, 99999);
        document.execCommand('copy');
      }
    }

    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, []);

  const handleInputClick = useCallback(() => {
    inputRef.current?.select();
  }, []);

  return (
    <div className="page-wrapper">
      <Card
        variant="modal"
        className="static translate-x-0 translate-y-0 left-auto top-auto bg-white overflow-y-auto p-10"
      >
        <CardContent className="flex flex-col items-center gap-6 p-0">
          <a
            href="https://edulution.io"
            target="_blank"
            rel="noopener noreferrer"
          >
            <img
              src="/img/edulution.io_USER_INTERFACE.svg"
              alt="edulution.io User Interface Logo"
              className="logo"
            />
          </a>

          <div className="w-full">
            <h2 className="text-center text-lg font-semibold text-[#2d3748] mb-4">Quick Install</h2>

            <div className="mb-5">
              <input
                ref={inputRef}
                type="text"
                value={INSTALL_COMMAND}
                readOnly
                onClick={handleInputClick}
                aria-label="Installation command"
                className="link-field"
              />
            </div>

            <Button
              variant="btn-security"
              size="lg"
              className="mx-auto w-full justify-center text-white shadow-xl"
              onClick={handleCopy}
            >
              {copied ? '\u2713 Kopiert!' : 'In Zwischenablage kopieren'}
            </Button>

            <div
              className={`copy-feedback ${copied ? 'show' : ''}`}
              role="status"
              aria-live="polite"
            >
              {copied ? 'In die Zwischenablage kopiert!' : ''}
            </div>
          </div>

          <div className="footer-section w-full">
            Alle Informationen auf{' '}
            <a
              href="https://edulution.io"
              target="_blank"
              rel="noopener noreferrer"
            >
              edulution.io
            </a>{' '}
            oder in der{' '}
            <a
              href="https://docs.edulution.io"
              target="_blank"
              rel="noopener noreferrer"
            >
              Dokumentation
            </a>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default App;

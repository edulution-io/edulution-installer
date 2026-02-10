import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';
import { faSpinner, faCircleCheck, faCircleXmark } from '@fortawesome/free-solid-svg-icons';
import { Button } from '@edulution-io/ui-kit';

interface StatusCardProps {
  label: string;
  status: { status: boolean; message: string } | null;
  loading: boolean;
  onRetry: () => void;
}

const StatusCard = ({ label, status, loading, onRetry }: StatusCardProps) => (
  <div className="flex items-center gap-3 rounded-lg border border-gray-200 bg-white p-3 shadow-sm">
    <div className="flex w-8 items-center justify-center text-xl">
      {loading && (
        <FontAwesomeIcon
          icon={faSpinner}
          spin
          className="text-gray-500"
        />
      )}
      {!loading && status?.status === true && (
        <FontAwesomeIcon
          icon={faCircleCheck}
          className="text-green-500"
        />
      )}
      {!loading && status !== null && !status.status && (
        <FontAwesomeIcon
          icon={faCircleXmark}
          className="text-red-500"
          title={status.message}
        />
      )}
    </div>

    <div className="flex-1 text-sm text-gray-800">{label}</div>

    {!loading && status !== null && !status.status && (
      <Button
        variant="btn-outline"
        size="sm"
        onClick={onRetry}
      >
        Erneut prüfen
      </Button>
    )}
  </div>
);

export default StatusCard;

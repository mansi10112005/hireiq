import { ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/primitives";
import { EmptyState } from "@/components/ui/states";

export default function ReportNotFound() {
  return (
    <Card>
      <EmptyState
        title="Report not found"
        description="This report does not exist, or it was deleted."
        action={<ButtonLink href="/results">Back to results</ButtonLink>}
      />
    </Card>
  );
}
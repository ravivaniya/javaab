import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Lock } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface Props {
  open: boolean;
  onOpenChange: (v: boolean) => void;
  feature: string;
}

/** Locked-feature upsell modal (camera/gallery/etc on Free). */
export function UpgradeModal({ open, onOpenChange, feature }: Props) {
  const nav = useNavigate();
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="rounded-3xl">
        <DialogHeader>
          <div className="mx-auto mb-2 inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-primary/10 text-primary">
            <Lock className="h-6 w-6" />
          </div>
          <DialogTitle className="text-center font-display text-2xl font-black tracking-tight">
            {feature} is a Plus feature
          </DialogTitle>
          <DialogDescription className="text-center">
            Upload images of textbook problems and get instant step-by-step solutions.
            Available on Plus & Pro.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter className="sm:justify-center">
          <Button
            variant="outline"
            className="rounded-pill"
            onClick={() => onOpenChange(false)}
          >
            Maybe later
          </Button>
          <Button
            className="rounded-pill"
            onClick={() => {
              onOpenChange(false);
              nav("/subscribe?plan=plus");
            }}
          >
            Upgrade to Plus
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

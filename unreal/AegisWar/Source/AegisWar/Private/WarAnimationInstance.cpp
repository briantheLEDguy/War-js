#include "WarAnimationInstance.h"
#include "WarCharacter.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimationPoseData.h"
#include "AnimationRuntime.h"
#include "Engine/World.h"
#include "GameFramework/GameStateBase.h"

namespace
{
    class FWarAnimationProxy final : public FAnimInstanceProxy
    {
    public:
        explicit FWarAnimationProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance) {}
        virtual void PreUpdate(UAnimInstance* Instance, float Delta) override
        {
            FAnimInstanceProxy::PreUpdate(Instance, Delta);
            auto* Animation = CastChecked<UWarAnimationInstance>(Instance);
            // Character movement may request a pose before the pawn's tick.
            // Select against the current clock at this game-thread boundary.
            Animation->PreparePose(Delta);
            Animation->Blend = FMath::Min(1.f, Animation->Blend + Delta / FMath::Max(.001f, Animation->BlendDuration));
            Current = Animation->Current; Previous = Animation->Previous;
            CurrentTime = Animation->CurrentTime; PreviousTime = Animation->PreviousTime; Blend = Animation->Blend;
            State = Animation->State;
            const auto* World=Instance->GetWorld();
            const auto* GameState=World ? World->GetGameState() : nullptr;
            SampledServerTime=GameState ? GameState->GetServerWorldTimeSeconds() : World ? World->GetTimeSeconds() : -1;
        }
        virtual void PostEvaluate(UAnimInstance* Instance) override
        {
            FAnimInstanceProxy::PostEvaluate(Instance);
            auto* Animation=CastChecked<UWarAnimationInstance>(Instance);
            // Publish only completed evaluation. A world subsystem can run before
            // this frame's parallel pose task; its clock is then one frame newer.
            Animation->EvaluatedState=State; Animation->EvaluatedTime=CurrentTime;
            Animation->EvaluatedServerTime=SampledServerTime;
        }
        virtual bool Evaluate(FPoseContext& Output) override
        {
            Output.ResetToRefPose();
            if (!Current) return true;
            FAnimationPoseData CurrentPose(Output);
            // Explicit extraction deliberately excludes notifies and root motion;
            // authoritative contact events cannot fire twice during a crossfade.
            Current->GetAnimationPose(CurrentPose, FAnimExtractContext(CurrentTime, false));
            if (Previous && Blend < 1)
            {
                FPoseContext Old(Output); Old.ResetToRefPose();
                FAnimationPoseData OldPose(Old);
                Previous->GetAnimationPose(OldPose, FAnimExtractContext(PreviousTime, false));
                FAnimationRuntime::BlendTwoPosesTogetherInPlace(CurrentPose, OldPose, Blend);
            }
            return true;
        }
    private:
        UAnimSequence* Current = nullptr;
        UAnimSequence* Previous = nullptr;
        float CurrentTime = 0, PreviousTime = 0, Blend = 1;
        double SampledServerTime = -1;
        FName State;
    };
}
void UWarAnimationInstance::PreparePose(float DeltaSeconds)
{
    if (auto* Character=Cast<AWarCharacter>(TryGetPawnOwner()); Character && Character->IsVisualReady())
        Character->UpdateNativeAnimation(DeltaSeconds);
}
void UWarAnimationInstance::Select(UAnimSequence* Sequence, FName NewState, float Time, float BlendSeconds)
{
    if (Current != Sequence || State != NewState)
    {
        Previous = Current; PreviousTime = CurrentTime; Blend = Previous ? 0 : 1;
        Current = Sequence; State = NewState; BlendDuration = FMath::Max(.001f, BlendSeconds);
    }
    CurrentTime = FMath::Clamp(Time, 0.f, Sequence ? Sequence->GetPlayLength() : 0.f);
}
FAnimInstanceProxy* UWarAnimationInstance::CreateAnimInstanceProxy() { return new FWarAnimationProxy(this); }
void UWarAnimationInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) { delete Proxy; }

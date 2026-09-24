#include "WarSiegeRules.h"

bool WarSiege::ValidCapacity(int32 N) { return N == 6 || N == 12 || N == 18; }
float WarSiege::HealthScale(int32 N) { return ValidCapacity(N) ? N / 6.f : 0.f; }
int32 WarSiege::Reinforcements(int32 N, bool Sabotaged)
{ return ValidCapacity(N) ? (Sabotaged ? N / 6 : N / 3) : 0; }
float WarSiege::ParticipationRate(int32 N, bool Escort)
{ return N <= 0 ? 0.f : FMath::Min(Escort ? 1.5f : 2.5f, 1.f + .25f * (N - 1)); }
int32 WarSiege::FinalObjective(int32 Stage) { return Stage == 0 ? 3 : Stage == 1 ? 2 : 0; }
bool WarSiege::IsEscort(const FWarSiegeState& S) { return S.Stage == 0 && (S.Objective == 1 || S.Objective == 2); }
bool WarSiege::Start(FWarSiegeState& S, int32 Capacity)
{
    if (!ValidCapacity(Capacity) || S.Phase == EWarSiegePhase::Active || S.Phase == EWarSiegePhase::Transition) return false;
    S = {}; S.Capacity = Capacity; S.Phase = EWarSiegePhase::Active; return true;
}
namespace
{
    void Capture(float& Progress, double& Absence, int32 Attackers, int32 Defenders, double Dt, bool Escort)
    {
        const double PreviousAbsence = Absence;
        Absence = Attackers > 0 ? 0 : Absence + Dt;
        if (Attackers > 0 && Defenders == 0)
            Progress = FMath::Min(1.f, Progress + float(Dt / 90 * WarSiege::ParticipationRate(Attackers, Escort)));
        else if (Attackers == 0 && !Escort)
            Progress = FMath::Max(0.f, Progress - float(.05 * (FMath::Max(0., Absence - 10) - FMath::Max(0., PreviousAbsence - 10))));
    }
    void Finish(FWarSiegeState& S, bool Won)
    { S.Phase = EWarSiegePhase::Finished; S.bAttackersWon = Won; S.Remaining = 0; ++S.ResultCount; }
}
void WarSiege::Tick(FWarSiegeState& S, const FWarSiegePresence& P, double Delta)
{
    if (!FMath::IsFinite(Delta) || Delta <= 0 || !ValidCapacity(S.Capacity)) return;
    // Fixed substeps make timeout/capture ordering independent of server frame rate.
    while (Delta > 0 && S.Phase != EWarSiegePhase::Finished && S.Phase != EWarSiegePhase::Waiting)
    {
        const double Dt = FMath::Min(Delta, .05); Delta -= Dt;
        if (S.Phase == EWarSiegePhase::Transition)
        {
            S.Remaining -= Dt;
            if (S.Remaining <= 1.e-6)
            { const int32 Next = S.Stage + 1, N = S.Capacity; S = {}; S.Stage = Next; S.Capacity = N; S.Phase = EWarSiegePhase::Active; return; }
            // Do not apply the previous stage's presence to the next stage.
            continue;
        }
        const bool Activity = S.Objective == FinalObjective(S.Stage)
            && (S.Stage == 2 ? P.bRecentCommanderDamage : P.Attackers > 0 && P.bCrewAlive);
        if (!S.bOptionalComplete)
        {
            Capture(S.OptionalProgress, S.OptionalAbsence, P.OptionalAttackers, P.OptionalDefenders, Dt, false);
            S.bOptionalComplete = S.OptionalProgress >= 1;
        }
        if (S.Stage < 2)
        {
            const bool CrewRequired = IsEscort(S) || S.Objective == FinalObjective(S.Stage);
            if (!CrewRequired || P.bCrewAlive) Capture(S.Progress, S.Absence, P.Attackers, P.Defenders, Dt, IsEscort(S));
            if (IsEscort(S) && !P.bEscortAtCheckpoint) S.Progress = FMath::Min(S.Progress, .99f);
            if (S.Progress >= 1)
            {
                if (S.Objective == FinalObjective(S.Stage))
                { S.Phase = EWarSiegePhase::Transition; S.Remaining = TransitionSeconds; S.bOvertime = false; }
                else { ++S.Objective; S.Progress = 0; S.Absence = 0; }
                return;
            }
        }
        else if (P.bCommanderDead) { Finish(S, true); return; }
        S.Remaining -= Dt;
        if (S.bOvertime)
        {
            S.OvertimeAbsence = Activity ? 0 : S.OvertimeAbsence + Dt;
            if (S.Remaining <= 1.e-6 || S.OvertimeAbsence >= 10) Finish(S, false);
        }
        else if (S.Remaining <= 1.e-6)
        {
            if (Activity) { S.bOvertime = true; S.Remaining = OvertimeSeconds; S.OvertimeAbsence = 0; }
            else Finish(S, false);
        }
    }
}
EWarSiegeRole WarSiege::MissingRole(int32 Capacity, int32 Tanks, int32 Healers)
{
    if (Tanks < Capacity / 6) return EWarSiegeRole::Tank;
    if (Healers < Capacity / 6) return EWarSiegeRole::Healer;
    return EWarSiegeRole::Damage;
}
EWarSiegeDecision WarSiege::Decide(bool Hazard, bool Recovering, float Hp, bool Threat, bool Objective, bool Leader)
{
    if (Hazard) return EWarSiegeDecision::Evade;
    if (Hp < .25f || (Recovering && Hp < .6f)) return EWarSiegeDecision::Recover;
    if (Threat) return EWarSiegeDecision::Combat;
    if (Objective || !Leader) return EWarSiegeDecision::Objective;
    return EWarSiegeDecision::Follow;
}

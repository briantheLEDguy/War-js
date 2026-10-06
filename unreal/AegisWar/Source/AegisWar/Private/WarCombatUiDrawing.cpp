#include "WarCombatUiDrawing.h"
#include "WarTargetReticle.h"
#include "GameFramework/HUD.h"
#include "Engine/Canvas.h"
#include "Engine/Engine.h"

namespace
{
    FLinearColor Tint(FLinearColor C,const FWarCombatUiStyle& S) { C.A*=S.Opacity; return C; }
    void Box(FWarCombatUiDrawList& D,int32 I,FVector2D P,FVector2D Size,FLinearColor C) { D.Items.Add({EWarUiDraw::Box,I,P,Size,C,TEXT(""),1}); }
    void Text(FWarCombatUiDrawList& D,int32 I,FVector2D P,float Width,const FString& Value,float Font,FLinearColor C)
    { D.Items.Add({EWarUiDraw::Text,I,P,FVector2D(Width,Font*1.4f),C,Value,Font}); }
    void Handle(FWarCombatUiDrawList& D,int32 I,FVector2D P,FVector2D Size) { D.Handles.Add(I,FBox2D(P,P+Size)); }
    void Bar(FWarCombatUiDrawList& D,int32 I,const FWarCombatUiStyle& S,FVector2D P,float Scale,float Fraction)
    {
        const FVector2D Size(S.Width*Scale,S.Height*Scale); Handle(D,I,P,Size); if (!S.Visible) return;
        const float Border=FMath::Min(S.Thickness*Scale,FMath::Min(Size.X,Size.Y)*.45);
        Box(D,I,P,Size,Tint(S.Colors[2],S));
        Box(D,I,P+FVector2D(Border),Size-FVector2D(Border*2),Tint(S.Colors[1],S));
        Box(D,I,P+FVector2D(Border),FVector2D((Size.X-2*Border)*FMath::Clamp(Fraction,0.f,1.f),Size.Y-2*Border),Tint(S.Colors[0],S));
    }
    void TextElement(FWarCombatUiDrawList& D,int32 I,const FWarCombatUiStyle& S,FVector2D P,float Scale,const FString& Value)
    {
        Handle(D,I,P,FVector2D(S.Width*Scale,S.Font*1.4f*Scale)); if (!S.Visible) return;
        if (S.Shadow) Text(D,I,P+FVector2D(Scale),S.Width*Scale,Value,S.Font*Scale,Tint(S.Colors[2],S));
        Text(D,I,P,S.Width*Scale,Value,S.Font*Scale,Tint(S.Colors[0],S));
    }
}
void WarCombatUi::Reticle(FWarCombatUiDrawList& D,const FWarCombatUiSettings& Settings,bool Enemy,FBox2D Body,float Scale)
{
    if (!Body.bIsValid) return;
    const int32 I=Id(EWarCombatUiPart::Reticle,Enemy); const auto& S=Settings.Styles[I];
    const FVector2D Center=Body.GetCenter()+FVector2D(S.X,S.Y)*Scale, Half=Body.GetSize()*.5*S.Scale+FVector2D(S.Padding*Scale);
    const FBox2D Rect(Center-Half,Center+Half); Handle(D,I,Rect.Min,Rect.GetSize()); if (!S.Visible) return;
    for (const auto& L:WarTargetReticle::Corners(Rect,Scale*S.Scale))
    {
        D.Items.Add({EWarUiDraw::Line,I,L.Key,L.Value,Tint(S.Colors[2],S),TEXT(""),(S.Thickness+4)*Scale});
        D.Items.Add({EWarUiDraw::Line,I,L.Key,L.Value,Tint(S.Colors[0],S),TEXT(""),S.Thickness*Scale});
    }
}
void WarCombatUi::HealthBar(FWarCombatUiDrawList& D,const FWarCombatUiSettings& Settings,bool Enemy,FVector2D Head,float Fraction,float Scale)
{
    const int32 I=Id(EWarCombatUiPart::OverheadHealth,Enemy); const auto& S=Settings.Styles[I];
    Bar(D,I,S,Head+FVector2D(S.X,S.Y)*Scale-FVector2D(S.Width*.5f,S.Height)*Scale*S.Scale,Scale*S.Scale,Fraction);
}
void WarCombatUi::Number(FWarCombatUiDrawList& D,const FWarCombatUiSettings& Settings,const FWarFloatingCombatNumber& N,FVector2D Head,float Scale)
{
    const int32 I=Id(N.Kind==TEXT("Heal")?EWarCombatUiPart::Healing:N.Kind==TEXT("CriticalHit")?EWarCombatUiPart::Critical:EWarCombatUiPart::Damage,N.bEnemy);
    const auto& S=Settings.Styles[I]; const float K=Scale*S.Scale;
    const FVector2D Origin=Head+FVector2D(S.X,S.Y)*Scale;
    const FBox2D Region(Origin-FVector2D(80,112)*K,Origin+FVector2D(80,0)*K);
    Handle(D,I,Region.Min,Region.GetSize()); if (!S.Visible) return;
    auto Styled=N; Styled.Rise=S.Rise;
    // Keep every rise setting inside the same bounded region, including the tallest font.
    Styled.Rise=FMath::Min(Styled.Rise,112.f-8.f-S.Font*1.4f-2.f);
    const FVector2D P=Origin+WarFloatingCombatText::Offset(Styled)*K-FVector2D(28,S.Font*1.4f)*K;
    const FString Value=FString::Printf(TEXT("%s%.0f"),N.Kind==TEXT("Heal")?TEXT("+"):TEXT(""),N.Amount);
    auto Style=S; Style.Opacity*=WarFloatingCombatText::Opacity(N);
    if (Style.Shadow) Text(D,I,P+FVector2D(K),56*K,Value,S.Font*K,Tint(S.Colors[2],Style));
    Text(D,I,P,56*K,Value,S.Font*K,Tint(S.Colors[0],Style));
}
void WarCombatUi::Panel(FWarCombatUiDrawList& D,const FWarCombatUiSettings& Settings,bool Enemy,FVector2D View,float Scale,const FString& Name,float Health,float Maximum,const FString& Cast,float Progress)
{
    const int32 I=Id(EWarCombatUiPart::Panel,Enemy); const auto& S=Settings.Styles[I]; const float K=Scale*S.Scale;
    const FVector2D P=FVector2D(S.X*View.X,S.Y*View.Y)-FVector2D(S.Width*K*.5,0), Size=FVector2D(S.Width,S.Height)*K;
    Handle(D,I,P,Size);
    if (S.Visible)
    {
        Box(D,I,P,Size,Tint(S.Colors[2],S)); const float B=FMath::Min(S.Thickness*K,FMath::Min(Size.X,Size.Y)*.45);
        Box(D,I,P+FVector2D(B),Size-FVector2D(B*2),Tint(S.Colors[1],S));
    }
    for (int32 C=6;C<10;++C)
    {
        const int32 J=Id(static_cast<EWarCombatUiPart>(C),Enemy); auto Child=Settings.Styles[J]; Child.Visible&=S.Visible; Child.Opacity*=S.Opacity;
        const FVector2D At=P+FVector2D(Child.X,Child.Y)*K; const float CK=K*Child.Scale;
        if (C==6) TextElement(D,J,Child,At,CK,(Enemy?TEXT("ENEMY  "):TEXT("ALLY  "))+Name.Left(32));
        if (C==7) Bar(D,J,Child,At,CK,Maximum>0?Health/Maximum:0);
        if (C==8) TextElement(D,J,Child,At,CK,FString::Printf(TEXT("%.0f / %.0f"),Health,Maximum));
        if (C==9)
        {
            Handle(D,J,At,FVector2D(Child.Width,Child.Font*1.4f+Child.Height+3)*CK);
            if (Child.Visible && !Cast.IsEmpty())
            {
                Text(D,J,At,Child.Width*CK,Cast.Left(32),Child.Font*CK,Tint(Child.Colors[0],Child));
                Bar(D,J,Child,At+FVector2D(0,(Child.Font*1.4f+3)*CK),CK,Progress);
                Handle(D,J,At,FVector2D(Child.Width,Child.Font*1.4f+Child.Height+3)*CK);
            }
        }
    }
}
void WarCombatUi::Notices(FWarCombatUiDrawList& D,const FWarCombatUiSettings& Settings,FVector2D View,float Scale,const TArray<FWarCombatNotice>& Events,double Now)
{
    const auto& Feed=Settings.Styles[21]; const float K=Scale*Feed.Scale;
    const FVector2D Origin(Feed.X*View.X-Feed.Width*K-6*Scale,Feed.Y*View.Y);
    const float Row=(Feed.Font*1.4f+4)*K; Handle(D,21,Origin,FVector2D(Feed.Width*K,Row*6));
    float Y=Origin.Y; float Flash=0; bool Critical=false;
    for (const auto& N:Events)
    {
        if (N.Expires<=Now) continue;
        const bool Hit=N.Kind==TEXT("Hit") || N.Kind==TEXT("CriticalHit");
        const float Age=Now-(N.Expires-3);
        if (Hit && Age<.18f && 1-Age/.18f>Flash) { Flash=1-Age/.18f; Critical=N.Kind==TEXT("CriticalHit"); }
        if (!Feed.Visible) continue;
        const int32 Color=N.Kind==TEXT("Heal")?4:N.Kind==TEXT("Interrupt")?2:N.Kind==TEXT("Guarded")?5:N.Kind==TEXT("CriticalHit")?3:0;
        const FString Value=N.Kind==TEXT("Interrupt")?TEXT("INTERRUPT - ")+N.Label:FString::Printf(TEXT("%s %.0f - %s"),*N.Kind.ToString(),N.Amount,*N.Label);
        Box(D,21,FVector2D(Origin.X,Y),FVector2D(Feed.Width*K,Row),Tint(Feed.Colors[1],Feed));
        Text(D,21,FVector2D(Origin.X+4*K,Y+2*K),(Feed.Width-8)*K,Value.Left(80),Feed.Font*K,Tint(Feed.Colors[Color],Feed)); Y+=Row;
    }
    const auto& Marker=Settings.Styles[20]; const float MK=Scale*Marker.Scale;
    const FVector2D Center(Marker.X*View.X,Marker.Y*View.Y), Half=FVector2D(Marker.Width,Marker.Height)*MK*(Critical?.75:.5);
    Handle(D,20,Center-Half,Half*2);
    if (Marker.Visible && Flash>0)
        for (int32 X:{-1,1}) for (int32 YSign:{-1,1})
        {
            auto C=Tint(Marker.Colors[Critical?3:0],Marker); C.A*=Flash;
            D.Items.Add({EWarUiDraw::Line,20,Center+FVector2D(X,YSign)*MK*5,Center+FVector2D(X*Half.X,YSign*Half.Y),C,TEXT(""),Marker.Thickness*MK*(Critical?1.5f:1.f)});
        }
}
void WarCombatUi::Canvas(AHUD* Hud,UCanvas* Canvas,const FWarCombatUiDrawList& D)
{
    if (!Hud || !Canvas || !GEngine) return;
    for (const auto& Item:D.Items)
    {
        const FVector2D End=Item.Kind==EWarUiDraw::Line?Item.B:Item.A+Item.B;
        if (FMath::Min(Item.A.X,End.X)<0 || FMath::Min(Item.A.Y,End.Y)<0 || FMath::Max(Item.A.X,End.X)>Canvas->SizeX || FMath::Max(Item.A.Y,End.Y)>Canvas->SizeY) continue;
        if (Item.Kind==EWarUiDraw::Box) Hud->DrawRect(Item.Color,Item.A.X,Item.A.Y,Item.B.X,Item.B.Y);
        else if (Item.Kind==EWarUiDraw::Line) Hud->DrawLine(Item.A.X,Item.A.Y,Item.B.X,Item.B.Y,Item.Color,Item.Weight);
        else
        {
            float W=0,H=0; Hud->GetTextSize(Item.Text,W,H,GEngine->GetMediumFont(),1);
            const float K=FMath::Min(Item.Weight/FMath::Max(1.f,H),static_cast<float>(Item.B.X)/FMath::Max(1.f,W));
            Hud->DrawText(Item.Text,Item.Color,Item.A.X,Item.A.Y,GEngine->GetMediumFont(),K);
        }
    }
}
int32 WarCombatUi::HitTest(const FWarCombatUiDrawList& D,FVector2D P)
{
    int32 Best=INDEX_NONE; double Area=MAX_dbl;
    for (const auto& Pair:D.Handles) if (Pair.Value.IsInsideOrOn(P))
    { const auto S=Pair.Value.GetSize(); const double A=S.X*S.Y; if (A<Area) { Area=A; Best=Pair.Key; } }
    return Best;
}
void FWarCombatUiPreview::Replay(int32 M) { Mode=FMath::Clamp(M,0,2); Time=0; NextProc=0; Paused=false; Numbers.Reset(); }
void FWarCombatUiPreview::Advance(float Delta,const FWarCombatUiSettings& S)
{
    Numbers.RemoveAll([&](const auto& N) {
        const auto Part=N.Kind==TEXT("Heal")?EWarCombatUiPart::Healing:N.Kind==TEXT("CriticalHit")?EWarCombatUiPart::Critical:EWarCombatUiPart::Damage;
        return !S.Styles[WarCombatUi::Id(Part,N.bEnemy)].Visible;
    });
    if (Paused || !FMath::IsFinite(Delta) || Delta<0) return;
    Time+=FMath::Min(Delta,1.f); if (Time>=4) { Time=FMath::Fmod(Time,4.); NextProc=0; Numbers.Reset(); }
    const int32 Count=Mode==1?20:1;
    while (NextProc<Count && NextProc*.05<=Time)
    {
        for (bool Enemy:{false,true})
        {
            const FName Kind=Mode==2?TEXT("Heal"):NextProc%5==4?TEXT("CriticalHit"):TEXT("Hit");
            const auto P=Kind==TEXT("Heal")?EWarCombatUiPart::Healing:Kind==TEXT("CriticalHit")?EWarCombatUiPart::Critical:EWarCombatUiPart::Damage;
            WarFloatingCombatText::Add(Numbers,Enemy?2:1,nullptr,FVector::ZeroVector,Kind,Kind==TEXT("CriticalHit")?248:126,NextProc*.05,Enemy,&S.Styles[WarCombatUi::Id(P,Enemy)]);
        }
        ++NextProc;
    }
    WarFloatingCombatText::Advance(Numbers,Time);
}
FWarCombatUiDrawList FWarCombatUiPreview::Draw(const FWarCombatUiSettings& Settings,FVector2D View,int32 Selected) const
{
    FWarCombatUiDrawList D;
    if (View.ContainsNaN() || View.X<=0 || View.Y<=0) return D;
    const float Scale=FMath::Clamp(static_cast<float>(View.Y/900),.8f,1.5f);
    for (bool Enemy:{false,true})
    {
        const FVector2D Head(View.X*(Enemy?.55:.30),View.Y*.36);
        const FVector2D Size(72*Scale,190*Scale); const FBox2D Body(Head+FVector2D(-Size.X*.5,15*Scale),Head+FVector2D(Size.X*.5,15*Scale)+Size);
        const FLinearColor C=Enemy?FLinearColor(1,.2f,.2f):FLinearColor(.15f,.55f,1);
        const FVector2D Neck=Head+FVector2D(0,48)*Scale;
        for (int32 N=0;N<24;++N)
        { const double A=N*2*PI/24,B=(N+1)*2*PI/24; const FVector2D Center=Head+FVector2D(0,28)*Scale;
            D.Items.Add({EWarUiDraw::Line,-1,Center+FVector2D(FMath::Cos(A),FMath::Sin(A))*17*Scale,Center+FVector2D(FMath::Cos(B),FMath::Sin(B))*17*Scale,C,TEXT(""),2}); }
        const FVector2D Waist=Head+FVector2D(0,135)*Scale;
        for (const auto& L:TArray<TPair<FVector2D,FVector2D>>{{Neck,Waist},{Neck+FVector2D(0,12)*Scale,Head+FVector2D(-36,115)*Scale},{Neck+FVector2D(0,12)*Scale,Head+FVector2D(36,115)*Scale},{Waist,Head+FVector2D(-28,205)*Scale},{Waist,Head+FVector2D(28,205)*Scale}})
            D.Items.Add({EWarUiDraw::Line,-1,L.Key,L.Value,C,TEXT(""),2});
        Text(D,-1,Head+FVector2D(-50,220)*Scale,140*Scale,Enemy?TEXT("ENEMY PREVIEW"):TEXT("FRIENDLY PREVIEW"),13*Scale,C);
        const float Health=Mode==2?40+FMath::Min(Time,1.)*50:100-FMath::Min(Time,1.)*60;
        WarCombatUi::Reticle(D,Settings,Enemy,Body,Scale); WarCombatUi::HealthBar(D,Settings,Enemy,Head,Health/100,Scale);
        for (const auto& N:Numbers) if (N.bEnemy==Enemy) WarCombatUi::Number(D,Settings,N,Head,Scale);
        // Each stream has a stable selectable region even between events or while hidden.
        for (auto P:{EWarCombatUiPart::Damage,EWarCombatUiPart::Critical,EWarCombatUiPart::Healing})
        {
            const int32 I=WarCombatUi::Id(P,Enemy);
            if (!D.Handles.Contains(I)) { FWarFloatingCombatNumber N; N.bEnemy=Enemy; N.Kind=P==EWarCombatUiPart::Healing?TEXT("Heal"):P==EWarCombatUiPart::Critical?TEXT("CriticalHit"):TEXT("Hit"); N.Amount=126;
                FWarCombatUiDrawList Temp; WarCombatUi::Number(Temp,Settings,N,Head,Scale); D.Handles.Append(Temp.Handles); if (Selected==I && Settings.Styles[I].Visible) D.Items.Append(Temp.Items); }
        }
    }
    // Only one selected target exists in gameplay. Separate coincident panels for comparison
    // in the editor without changing either saved screen position or child-relative layout.
    auto Comparison=Settings;
    FWarCombatUiDrawList PanelBounds;
    for (bool Enemy:{false,true}) WarCombatUi::Panel(PanelBounds,Settings,Enemy,View,Scale,TEXT(""),0,100,TEXT(""),0);
    const bool Overlap=PanelBounds.Handles[5].Intersect(PanelBounds.Handles[15]);
    if (Overlap)
    {
        const float Half=FMath::Max(PanelBounds.Handles[5].GetSize().X,PanelBounds.Handles[15].GetSize().X)*.5f+8*Scale;
        Comparison.Styles[5].X-=Half/View.X; Comparison.Styles[15].X+=Half/View.X;
    }
    for (bool Enemy:{false,true})
    {
        const float Health=Mode==2?40+FMath::Min(Time,1.)*50:100-FMath::Min(Time,1.)*60;
        WarCombatUi::Panel(D,Comparison,Enemy,View,Scale,Enemy?TEXT("Enemy target"):TEXT("Friendly target"),Health,100,TEXT("Casting preview"),FMath::Fmod(Time,2.)/2);
    }
    if (Overlap) Text(D,-1,FVector2D(View.X*.5-180*Scale,118*Scale),360*Scale,TEXT("Panels share a position; separated here for comparison"),11*Scale,FLinearColor(.75f,.78f,.85f));
    TArray<FWarCombatNotice> Events={{TEXT("Hit"),TEXT("Enemy target"),126,Time+2.93},{TEXT("CriticalHit"),TEXT("Enemy target"),248,Time+2.8},{TEXT("Heal"),TEXT("Friendly target"),90,Time+2.7},{TEXT("Interrupt"),TEXT("Enemy cast"),0,Time+2},{TEXT("Guarded"),TEXT("Protected"),35,Time+1.5}};
    WarCombatUi::Notices(D,Settings,View,Scale,Events,Time);
    return D;
}
FBox2D WarCombatUi::ElementBounds(int32 I,const FWarCombatUiSettings& S,FVector2D View,float Scale)
{ FWarCombatUiPreview P; const auto D=P.Draw(S,View,I); const auto* B=D.Handles.Find(I); return B?*B:FBox2D(ForceInit); }
